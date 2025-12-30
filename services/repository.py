from typing import List, Optional, Tuple, Dict, Union
from dataclasses import dataclass
import uuid

# Import the NEW Polymorphic Entities
from models.entities import (
    DatasetContent, Project, Goal,
    TaskItem, ResourceItem, ReferenceItem, ProjectItem,
    ProjectStatus, ResourceType
)
from models.ai_schemas import ClassificationResult, ClassificationType
from services.services import DatasetManager


# --- THE PROPOSAL OBJECT (Buffer) ---
@dataclass
class DraftItem:
    """
    Represents an item that has been proposed by AI but not yet
    committed to the database.
    """
    source_text: str
    classification: ClassificationResult

    def to_entity(self) -> ProjectItem:
        """Factory method to convert the draft into a concrete Entity"""
        kind = self.classification.classification_type
        name = self.classification.refined_text or self.source_text
        tags = self.classification.extracted_tags

        # Extract duration (default to 'unknown' if missing)
        duration = self.classification.estimated_duration or "unknown"

        if kind == ClassificationType.INCUBATE:
            return TaskItem(
                name=name,
                tags=["someday"],
                duration="unknown",
                notes="Incubated from Triage"
            )
        elif kind == ClassificationType.SHOPPING:
            return ResourceItem(name=name, store="General")

        elif kind == ClassificationType.REFERENCE:
            return ReferenceItem(name=name, content=self.source_text)

        else:
            # Map duration here
            return TaskItem(
                name=name,
                tags=tags,
                duration=duration  # <--- MAPPED
            )


# --- REPOSITORY ---
class YamlRepository:
    def __init__(self, dataset_manager: DatasetManager, current_dataset_name: str):
        self.dm = dataset_manager
        self.name = current_dataset_name
        self.data: DatasetContent = self.dm.load_dataset(current_dataset_name)

        # STATE MANAGEMENT
        self._is_dirty = False

        # INDEXING (Updated for Polymorphism)
        # Maps ItemID -> (Project, Item)
        self._item_index: Dict[str, Tuple[Project, ProjectItem]] = {}
        self._rebuild_index()

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def mark_dirty(self):
        self._is_dirty = True

    def save(self):
        """Explicit Save"""
        if self._is_dirty:
            self.dm.save_dataset(self.name, self.data)
            self._is_dirty = False

    def _rebuild_index(self):
        self._item_index.clear()
        for p in self.data.projects:
            for item in p.items:
                self._item_index[item.id] = (p, item)

    def find_project(self, project_id: int) -> Optional[Project]:
        return next((p for p in self.data.projects if p.id == project_id), None)

    def find_project_by_name(self, name: str) -> Optional[Project]:
        return next((p for p in self.data.projects if p.name == name), None)

    def find_item(self, item_id: str) -> Optional[ProjectItem]:
        if item_id in self._item_index:
            return self._item_index[item_id][1]
        return None

    def register_item(self, project: Project, item: ProjectItem):
        """Update index and dirty flag"""
        self._item_index[item.id] = (project, item)
        self.mark_dirty()


# --- SERVICES ---

class TriageService:
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_inbox_items(self) -> List[str]:
        return self.repo.data.inbox_tasks

    def add_to_inbox(self, text: str) -> None:
        self.repo.data.inbox_tasks.append(text)
        self.repo.mark_dirty()

    def delete_inbox_item(self, item_text: str) -> None:
        """
        Manual Only: Permanently removes item from system (Trash).
        """
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.mark_dirty()

    def create_draft(self, text: str, classification: ClassificationResult) -> DraftItem:
        """Pure function: Creates a proposal object"""
        return DraftItem(source_text=text, classification=classification)

    def apply_draft(self, draft: DraftItem, override_project_id: Optional[int] = None) -> None:
        """
        Commits a Draft to the database.
        """
        # 1. Determine Project
        project = None
        if override_project_id:
            project = self.repo.find_project(override_project_id)
        elif draft.classification.suggested_project != "Unmatched":
            project = self.repo.find_project_by_name(draft.classification.suggested_project)

        if not project:
            raise ValueError("Target project not found")

        # 2. Create Entity (Polymorphic)
        new_item = draft.to_entity()

        # 3. Add to Unified Stream
        project.items.append(new_item)
        self.repo.register_item(project, new_item)

        # 4. Remove from Inbox
        if draft.source_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(draft.source_text)
            self.repo.mark_dirty()

    def create_project_from_draft(self, draft: DraftItem, new_project_name: str) -> None:
        # 1. Create Project
        existing_ids = [p.id for p in self.repo.data.projects]
        new_id = max(existing_ids, default=0) + 1
        new_proj = Project(id=new_id, name=new_project_name)
        self.repo.data.projects.append(new_proj)

        # 2. Apply Draft to new project
        self.apply_draft(draft, override_project_id=new_id)

    def skip_inbox_item(self, item_text: str) -> None:
        # Rotate to end
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.data.inbox_tasks.append(item_text)
            self.repo.mark_dirty()

    def move_inbox_item_to_project(self, item_text: str, project_id: int, tags: List[str]) -> None:
        """
        Convenience method: Move inbox item directly to a project as a TaskItem.
        Used for manual assignment when user overrides AI suggestion.
        """
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Create TaskItem directly (simpler for manual assignment)
        task_item = TaskItem(name=item_text, tags=tags)
        project.items.append(task_item)
        self.repo.register_item(project, task_item)
        
        # Remove from inbox
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.mark_dirty()

    def create_project_from_inbox(self, item_text: str, new_project_name: str) -> None:
        """
        Convenience method: Create a new project and move inbox item to it.
        """
        # Create Project
        existing_ids = [p.id for p in self.repo.data.projects]
        new_id = max(existing_ids, default=0) + 1
        new_proj = Project(id=new_id, name=new_project_name)
        self.repo.data.projects.append(new_proj)
        self.repo.mark_dirty()
        
        # Create TaskItem and add to new project
        task_item = TaskItem(name=item_text)
        new_proj.items.append(task_item)
        self.repo.register_item(new_proj, task_item)
        
        # Remove from inbox
        if item_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.mark_dirty()

    def _build_hierarchy_context(self) -> str:
        lines = []
        # 1. Active Goals and their Projects
        for goal in self.repo.data.goals:
            lines.append(f"GOAL: {goal.name}")
            if goal.description:
                lines.append(f"  Desc: {goal.description}")

            projects = [p for p in self.repo.data.projects if p.goal_id == goal.id]
            for p in projects:
                lines.append(f"  - PROJECT: {p.name}")

        # 2. Orphaned Projects
        orphans = [p for p in self.repo.data.projects if not p.goal_id]
        if orphans:
            lines.append("NO GOAL (Maintenance/Misc):")
            for p in orphans:
                lines.append(f"  - PROJECT: {p.name}")

        return "\n".join(lines)

class PlanningService:
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_all_goals(self) -> List[Goal]:
        return self.repo.data.goals

    def create_goal(self, name: str, description: str) -> Goal:
        new_goal = Goal(name=name, description=description)
        self.repo.data.goals.append(new_goal)
        self.repo.mark_dirty()
        return new_goal

    def add_manual_item(self, project_id: int, kind: str, name: str, **kwargs) -> None:
        """Manual entry bypassing AI"""
        project = self.repo.find_project(project_id)
        if not project: return

        item = None
        if kind == "task":
            item = TaskItem(name=name, tags=kwargs.get('tags', []))
        elif kind == "resource":
            item = ResourceItem(name=name, store=kwargs.get('store', 'General'))
        elif kind == "reference":
            item = ReferenceItem(name=name, content=kwargs.get('content', ''))

        if item:
            project.items.append(item)
            self.repo.register_item(project, item)

    def get_projects_for_goal(self, goal_id: str) -> List[Project]:
        """Get all projects linked to a specific goal"""
        return [p for p in self.repo.data.projects if p.goal_id == goal_id]

    def get_orphaned_projects(self) -> List[Project]:
        """Get all projects not linked to any goal"""
        return [p for p in self.repo.data.projects if p.goal_id is None]

    def add_resource(self, project_id: int, name: str, r_type: ResourceType, store: str = "General") -> None:
        """Add a ResourceItem to a project's unified stream"""
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        resource_item = ResourceItem(name=name, type=r_type, store=store)
        project.items.append(resource_item)
        self.repo.register_item(project, resource_item)

    def add_reference_item(self, project_id: int, name: str, description: str) -> None:
        """Add a ReferenceItem to a project's unified stream"""
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        reference_item = ReferenceItem(name=name, content=description)
        project.items.append(reference_item)
        self.repo.register_item(project, reference_item)

    def link_project_to_goal(self, project_id: int, goal_id: Optional[str]) -> None:
        """Link a project to a goal (or unlink if goal_id is None)"""
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Verify goal exists if provided
        if goal_id is not None:
            goal_exists = any(g.id == goal_id for g in self.repo.data.goals)
            if not goal_exists:
                raise ValueError(f"Goal {goal_id} not found")
        
        project.goal_id = goal_id
        self.repo.mark_dirty()

    def complete_item(self, item_id: str) -> None:
        """Toggle completion status of an item"""
        item = self.repo.find_item(item_id)
        if not item:
            print(f"Error: Item {item_id} not found during completion toggle.")
            return

        if isinstance(item, TaskItem):
            item.is_completed = not item.is_completed
            self.repo.mark_dirty()
        elif isinstance(item, ResourceItem):
            item.is_acquired = not item.is_acquired
            self.repo.mark_dirty()

    def move_project(self, project_id: int, direction: str):
        """
        Moves a project 'up' or 'down' within its Goal group.
        """
        target_proj = self.repo.find_project(project_id)
        if not target_proj: return

        # 1. Get all projects in the same context (same Goal or same Orphaned state)
        siblings = [
            p for p in self.repo.data.projects
            if p.goal_id == target_proj.goal_id
        ]

        # 2. Sort them by current order
        siblings.sort(key=lambda p: p.sort_order)

        try:
            idx = siblings.index(target_proj)
        except ValueError:
            return

        # 3. Swap Logic
        if direction == "up" and idx > 0:
            # Swap sort_order with the one above
            neighbor = siblings[idx - 1]
            target_proj.sort_order, neighbor.sort_order = neighbor.sort_order, target_proj.sort_order
            self.repo.mark_dirty()

        elif direction == "down" and idx < len(siblings) - 1:
            # Swap sort_order with the one below
            neighbor = siblings[idx + 1]
            target_proj.sort_order, neighbor.sort_order = neighbor.sort_order, target_proj.sort_order
            self.repo.mark_dirty()

class ExecutionService:
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_next_actions(self, context_filter: Optional[str] = None) -> List[TaskItem]:
        """Filter the unified stream for Tasks only"""
        actions = []
        for p in self.repo.data.projects:
            if p.status != ProjectStatus.ACTIVE: continue

            # Iterate Unified Stream
            for item in p.items:
                # Check Type
                if isinstance(item, TaskItem) and not item.is_completed:
                    if context_filter and context_filter not in item.tags:
                        continue
                    actions.append(item)
        return actions

    def complete_item(self, item_id: str) -> None:
        item = self.repo.find_item(item_id)
        # Polymorphic completion
        if isinstance(item, TaskItem):
            item.is_completed = True
            self.repo.mark_dirty()
        elif isinstance(item, ResourceItem):
            item.is_acquired = True
            self.repo.mark_dirty()

    def get_shopping_list(self) -> Dict[str, List[Tuple[ResourceItem, str]]]:
        from collections import defaultdict
        shopping = defaultdict(list)

        for p in self.repo.data.projects:
            if p.status == ProjectStatus.COMPLETED: continue

            for item in p.items:
                if isinstance(item, ResourceItem) and not item.is_acquired:
                    shopping[item.store].append((item, p.name))

        return dict(shopping)

    def get_aggregated_shopping_list(self) -> Dict[str, List[Tuple[ResourceItem, str]]]:
        """Alias for get_shopping_list() to match view expectations"""
        return self.get_shopping_list()

    def toggle_resource_status(self, resource_id: str, is_acquired: bool) -> None:
        """Toggle the acquired status of a ResourceItem"""
        item = self.repo.find_item(resource_id)
        if isinstance(item, ResourceItem):
            item.is_acquired = is_acquired
            self.repo.mark_dirty()
        else:
            raise ValueError(f"Item {resource_id} is not a ResourceItem")
