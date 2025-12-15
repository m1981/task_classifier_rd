# services/repository.py
from typing import List, Optional, Tuple
from models.entities import Task, Project, Goal, DatasetContent, ProjectResource, ResourceType, ProjectStatus
from interfaces import InboxManager, GoalPlanner, TaskExecutor
from services.services import DatasetManager


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

    def save(self):
        self.dm.save_dataset(self.name, self.data)

    def find_project(self, project_id: int) -> Optional[Project]:
        return next((p for p in self.data.projects if p.id == project_id), None)

    def find_task(self, project_id: int, task_id: int) -> Optional[Task]:
        p = self.find_project(project_id)
        if p:
            return next((t for t in p.tasks if t.id == task_id), None)
        return None


# --- Service Implementations ---

class TriageService(InboxManager):
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_inbox_items(self) -> List[str]:
        return self.repo.data.inbox_tasks

    def add_to_inbox(self, text: str) -> None:
        self.repo.data.inbox_tasks.append(text)
        self.repo.save()

    def move_inbox_item_to_project(self, item_text: str, project_id: int, tags: List[str]) -> None:
        project = self.repo.find_project(project_id)
        if project:
            new_id = max([t.id for t in project.tasks], default=0) + 1
            new_task = Task(id=new_id, name=item_text, tags=tags)
            project.tasks.append(new_task)

            if item_text in self.repo.data.inbox_tasks:
                self.repo.data.inbox_tasks.remove(item_text)
            self.repo.save()

    def create_project_from_inbox(self, item_text: str, new_project_name: str) -> None:
        new_id = max([p.id for p in self.repo.data.projects], default=0) + 1
        new_proj = Project(id=new_id, name=new_project_name)
        self.repo.data.projects.append(new_proj)
        self.move_inbox_item_to_project(item_text, new_id, [])

    def skip_inbox_item(self, item_text: str) -> None:
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.data.inbox_tasks.append(item_text)
            self.repo.save()


class PlanningService(GoalPlanner):
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_all_goals(self) -> List[Goal]:
        return self.repo.data.goals

    def create_goal(self, name: str, description: str) -> Goal:
        # Simple ID generation
        import uuid
        new_goal = Goal(id=str(uuid.uuid4()), name=name, description=description)
        self.repo.data.goals.append(new_goal)
        self.repo.save()
        return new_goal

    def get_projects_for_goal(self, goal_id: str) -> List[Project]:
        return [p for p in self.repo.data.projects if p.goal_id == goal_id]

    def get_orphaned_projects(self) -> List[Project]:
        return [p for p in self.repo.data.projects if not p.goal_id]

    def add_resource(self, project_id: int, name: str, r_type: ResourceType, store: str = "General") -> None:
        project = self.repo.find_project(project_id)
        if project:
            res = ProjectResource(name=name, type=r_type, store=store)
            project.resources.append(res)
            self.repo.save()

    def add_reference_item(self, project_id: int, name: str, description: str) -> None:
        project = self.repo.find_project(project_id)
        if project:
            ref = ReferenceItem(name=name, description=description)
            project.reference_items.append(ref)
            self.repo.save()


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

    def complete_task(self, project_id: int, task_id: int) -> None:
        task = self.repo.find_task(project_id, task_id)
        if task:
            task.is_completed = True
            self.repo.save()

    def undo_complete_task(self, project_id: int, task_id: int) -> None:
        task = self.repo.find_task(project_id, task_id)
        if task:
            task.is_completed = False
            self.repo.save()

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

    def toggle_resource_status(self, resource_id: str, is_acquired: bool) -> None:
        # This is inefficient (O(N^2)) but fine for local YAML datasets
        for project in self.repo.data.projects:
            for res in project.resources:
                if res.id == resource_id:
                    res.is_acquired = is_acquired
                    self.repo.save()
                    return