from typing import List, Optional, Tuple, Dict
from models.entities import Task, Project, Goal, ProjectResource, ResourceType, ProjectStatus, ReferenceItem, DatasetContent
from interfaces import InboxManager, GoalPlanner, TaskExecutor
from services.services import DatasetManager
from services.decorators import autosave


class YamlRepository:
    """
    The 'God Object' wrapper.
    In a real app, this would handle DB connections.
    Here, it wraps the in-memory DatasetContent and handles saving.
    """

    def __init__(self, dataset_manager: DatasetManager, current_dataset_name: str):
        self.dm = dataset_manager
        self.name = current_dataset_name
        # Load initial state
        self.data: DatasetContent = self.dm.load_dataset(current_dataset_name)

        # OPTIMIZATION: Build an internal index for O(1) lookups
        # This maps TaskID -> (Project, Task)
        self._task_index: Dict[str, Tuple[Project, Task]] = {}
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuilds the internal lookup index. Call this after bulk operations."""
        self._task_index.clear()
        for p in self.data.projects:
            for t in p.tasks:
                self._task_index[t.id] = (p, t)

    def save(self):
        self.dm.save_dataset(self.name, self.data)

    def find_project(self, project_id: int) -> Optional[Project]:
        return next((p for p in self.data.projects if p.id == project_id), None)

    def get_task_parent(self, task_id: str) -> Optional[Project]:
        if task_id in self._task_index:
            return self._task_index[task_id][0]  # Returns the Project
        return None

    def find_task(self, project_id: int, task_id: str) -> Optional[Task]:
        # Fast lookup using index
        if task_id in self._task_index:
            return self._task_index[task_id][1]

        # Fallback (in case index is stale)
        p = self.find_project(project_id)
        if p:
            return next((t for t in p.tasks if t.id == task_id), None)
        return None

    def register_new_task(self, project: Project, task: Task):
        """Helper to keep index in sync when adding tasks"""
        self._task_index[task.id] = (project, task)


# --- Service Implementations ---

class TriageService(InboxManager):
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_inbox_items(self) -> List[str]:
        return self.repo.data.inbox_tasks

    @autosave
    def add_to_inbox(self, text: str) -> None:
        self.repo.data.inbox_tasks.append(text)

    @autosave
    def move_inbox_item_to_project(self, item_text: str, project_id: int, tags: List[str]) -> None:
        project = self.repo.find_project(project_id)
        if project:
            new_task = Task(name=item_text, tags=tags)
            project.tasks.append(new_task)
            self.repo.register_new_task(project, new_task) # Update Index

            if item_text in self.repo.data.inbox_tasks:
                self.repo.data.inbox_tasks.remove(item_text)

    @autosave
    def create_project_from_inbox(self, item_text: str, new_project_name: str) -> None:
        # Safe ID generation for Integers
        existing_ids = [p.id for p in self.repo.data.projects]
        new_id = max(existing_ids, default=0) + 1

        new_proj = Project(id=new_id, name=new_project_name)
        self.repo.data.projects.append(new_proj)

        # Reuse the move logic (which handles autosave, but since we are inside
        # an autosave function, we just call the logic directly to avoid double save)
        self.move_inbox_item_to_project(item_text, new_id, [])

    @autosave
    def skip_inbox_item(self, item_text: str) -> None:
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.data.inbox_tasks.append(item_text)


class PlanningService(GoalPlanner):
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_all_goals(self) -> List[Goal]:
        return self.repo.data.goals

    @autosave
    def create_goal(self, name: str, description: str) -> Goal:
        import uuid
        new_goal = Goal(id=str(uuid.uuid4()), name=name, description=description)
        self.repo.data.goals.append(new_goal)
        return new_goal

    def get_projects_for_goal(self, goal_id: str) -> List[Project]:
        return [p for p in self.repo.data.projects if p.goal_id == goal_id]

    def get_orphaned_projects(self) -> List[Project]:
        return [p for p in self.repo.data.projects if not p.goal_id]

    @autosave
    def add_resource(self, project_id: int, name: str, r_type: ResourceType, store: str = "General") -> None:
        project = self.repo.find_project(project_id)
        if project:
            res = ProjectResource(name=name, type=r_type, store=store)
            project.resources.append(res)

    @autosave
    def add_reference_item(self, project_id: int, name: str, description: str) -> None:
        project = self.repo.find_project(project_id)
        if project:
            ref = ReferenceItem(name=name, description=description)
            project.reference_items.append(ref)


class ExecutionService(TaskExecutor):
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_next_actions(self, context_filter: Optional[str] = None) -> List[Task]:
        all_tasks = []
        for project in self.repo.data.projects:
            if project.status != ProjectStatus.ACTIVE:
                continue
            for task in project.tasks:
                if not task.is_completed:
                    if context_filter and context_filter not in task.tags:
                        continue
                    all_tasks.append(task)
        return all_tasks

    @autosave
    def complete_task(self, project_id: int, task_id: str) -> None:
        # Note: task_id is now str (UUID)
        task = self.repo.find_task(project_id, task_id)
        if task:
            task.is_completed = True

    @autosave
    def undo_complete_task(self, project_id: int, task_id: str) -> None:
        task = self.repo.find_task(project_id, task_id)
        if task:
            task.is_completed = False

    def get_aggregated_shopping_list(self) -> dict[str, List[Tuple[ProjectResource, str]]]:
        from collections import defaultdict
        shopping_trip = defaultdict(list)

        for project in self.repo.data.projects:
            if project.status == ProjectStatus.COMPLETED:
                continue

            # Filter for TO_BUY and NOT acquired
            to_buy = [r for r in project.resources
                      if r.type == ResourceType.TO_BUY and not r.is_acquired]

            for item in to_buy:
                store_name = item.store if item.store else "General"
                shopping_trip[store_name].append((item, project.name))

        return dict(shopping_trip)

    @autosave
    def toggle_resource_status(self, resource_id: str, is_acquired: bool) -> None:
        # Optimization: We could index resources too, but N is usually small here.
        for project in self.repo.data.projects:
            for res in project.resources:
                if res.id == resource_id:
                    res.is_acquired = is_acquired
                    return