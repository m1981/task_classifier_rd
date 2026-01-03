from typing import List, Optional, Tuple, Dict, Union
from dataclasses import dataclass
import uuid
import logging

# Import the NEW Polymorphic Entities
from models.entities import (
    DatasetContent, Project, Goal,
    TaskItem, ResourceItem, ReferenceItem, ProjectItem,
    ProjectStatus, ResourceType
)
from models.ai_schemas import ClassificationResult, ClassificationType
from services.services import DatasetManager
import logging

logger = logging.getLogger("Repository")

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

        notes = self.classification.notes
        duration = self.classification.estimated_duration or "unknown"

        logger.debug(f"Converting DraftItem to Entity. Kind: {kind}, Name: {name}")

        if kind == ClassificationType.INCUBATE:
            return TaskItem(
                name=name,
                tags=["someday"] + tags,
                duration="unknown",
                notes=f"Incubated from Triage. {notes}".strip()
            )
        elif kind == ClassificationType.SHOPPING:
            return ResourceItem(
                name=name,
                store="General",
                tags=tags
            )

        elif kind == ClassificationType.REFERENCE:
            content_val = notes if notes else self.source_text
            return ReferenceItem(
                name=name,
                content=content_val,
                tags=tags
            )

        else:
            return TaskItem(
                name=name,
                tags=tags,
                duration=duration,
                notes=notes
            )

# --- REPOSITORY ---
class YamlRepository:
    def __init__(self, dataset_manager: DatasetManager, current_dataset_name: str):
        self.dm = dataset_manager
        self.name = current_dataset_name

        logger.info(f"Initializing Repository with dataset: {self.name}")
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
        if not self._is_dirty:
            logger.debug("Repository marked as dirty.")
        self._is_dirty = True

    def save(self):
        """Explicit Save"""
        if self._is_dirty:
            logger.info(f"Persisting dataset '{self.name}' to storage.")
            self.dm.save_dataset(self.name, self.data)
            self._is_dirty = False
        else:
            logger.debug("Save requested, but repository is clean. Skipping.")

    def _rebuild_index(self):
        logger.debug("Rebuilding item index.")
        self._item_index.clear()
        count = 0
        for p in self.data.projects:
            for item in p.items:
                self._item_index[item.id] = (p, item)
                count += 1
        logger.debug(f"Index rebuild complete. Indexed {count} items.")

    def find_project(self, project_id: int) -> Optional[Project]:
        return next((p for p in self.data.projects if p.id == project_id), None)

    def find_project_by_name(self, name: str) -> Optional[Project]:
        return next((p for p in self.data.projects if p.name == name), None)

    def find_item(self, item_id: str) -> Optional[ProjectItem]:
        if item_id in self._item_index:
            return self._item_index[item_id][1]
        logger.debug(f"Item lookup failed for ID: {item_id}")
        return None

    def register_item(self, project: Project, item: ProjectItem):
        """Update index and dirty flag"""
        logger.debug(f"Registering new item '{item.name}' ({item.id}) to Project '{project.name}'")
        self._item_index[item.id] = (project, item)
        self.mark_dirty()


# --- SERVICES ---

class TriageService:
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_inbox_items(self) -> List[str]:
        return self.repo.data.inbox_tasks

    def add_to_inbox(self, text: str) -> None:
        logger.info(f"Adding new item to Inbox: '{text[:30]}...'")
        self.repo.data.inbox_tasks.append(text)
        self.repo.mark_dirty()

    def delete_inbox_item(self, item_text: str) -> None:
        """
        Manual Only: Permanently removes item from system (Trash).
        """
        if item_text in self.repo.data.inbox_tasks:
            logger.info(f"Deleting item from Inbox: '{item_text[:30]}...'")
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.mark_dirty()
        else:
            logger.warning(f"Attempted to delete inbox item '{item_text[:30]}...' but it was not found.")

    def create_draft(self, text: str, classification: ClassificationResult) -> DraftItem:
        """Pure function: Creates a proposal object"""
        logger.debug(f"Creating draft for: '{text[:20]}...' as {classification.classification_type}")
        return DraftItem(source_text=text, classification=classification)

    def apply_draft(self, draft: DraftItem, override_project_id: Optional[int] = None) -> None:
        """
        Commits a Draft to the database.
        """
        logger.info(f"Applying draft. Source: '{draft.source_text[:30]}...'")

        # 1. Determine Project
        project = None
        if override_project_id:
            project = self.repo.find_project(override_project_id)
        elif draft.classification.suggested_project != "Unmatched":
            target_name = draft.classification.suggested_project
            project = self.repo.find_project_by_name(target_name)

            # =================================================================
            # 🛡️ FIX: AUTO-CREATE SYSTEM BUCKETS
            # If AI suggests a standard GTD bucket that doesn't exist yet, create it.
            # =================================================================
            if not project and target_name in ["General", "Someday/Maybe", "Inbox"]:
                logger.info(f"Auto-creating missing system project: '{target_name}'")

                # Generate new ID
                existing_ids = [p.id for p in self.repo.data.projects]
                new_id = max(existing_ids, default=0) + 1

                # Create and Register
                project = Project(id=new_id, name=target_name, description="System generated container")
                self.repo.data.projects.append(project)
                self.repo.mark_dirty()
            # =================================================================

        if not project:
            logger.error(f"Target project not found for draft: '{draft.source_text}' -> '{draft.classification.suggested_project}'")
            raise ValueError("Target project not found")

        # 2. Create Entity (Polymorphic)
        new_item = draft.to_entity()

        # 3. Add to Unified Stream
        project.items.append(new_item)
        self.repo.register_item(project, new_item)
        logger.info(f"Item '{new_item.name}' added to Project '{project.name}'")

        # 4. Remove from Inbox
        if draft.source_text in self.repo.data.inbox_tasks:
            self.repo.data.inbox_tasks.remove(draft.source_text)
            self.repo.mark_dirty()

    def create_project_from_draft(self, draft: DraftItem, new_project_name: str) -> None:
        logger.info(f"Creating new project from draft: '{new_project_name}'")
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
            logger.debug(f"Rotating inbox item: '{item_text[:20]}...'")
            self.repo.data.inbox_tasks.remove(item_text)
            self.repo.data.inbox_tasks.append(item_text)
            self.repo.mark_dirty()

    def move_inbox_item_to_project(self, item_text: str, project_id: int, tags: List[str]) -> None:
        """
        Convenience method: Move inbox item directly to a project as a TaskItem.
        """
        logger.info(f"Manually moving inbox item to Project ID {project_id}")
        project = self.repo.find_project(project_id)
        if not project:
            logger.error(f"Project {project_id} not found during manual move.")
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
        logger.info(f"Creating project '{new_project_name}' from inbox item.")
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

    def get_all_tags(self) -> List[str]:
        tags = set()
        for p in self.repo.data.projects:
            for item in p.items:
                if hasattr(item, 'tags'):
                    tags.update(item.tags)
        return list(tags)

    def build_full_context_tree(self) -> str:
        """
        Builds a rich, indented text tree of Goals > Projects > Active Items.
        """
        logger.debug("Building full context tree for AI context.")
        lines = ["```"]  # Start Code Block

        # Helper to format items
        def _append_items(project, indent="    "):
            # Filter for incomplete tasks/resources only
            active_items = [i for i in project.items if
                            not getattr(i, 'is_completed', False) and not getattr(i, 'is_acquired', False)]

            if not active_items:
                lines.append(f"{indent}(No active items)")
                return

            for item in active_items:
                if item.kind == 'task':
                    tags_str = ", ".join(item.tags) if item.tags else "no-tags"
                    lines.append(f"{indent}- {item.name}: {item.duration}, [{tags_str}]")
                elif item.kind == 'resource':
                    lines.append(f"{indent}- {item.name}: {item.store} (Resource)")
                elif item.kind == 'reference':
                    lines.append(f"{indent}- {item.name} (Reference)")

        # 1. Process Goals
        for goal in self.repo.data.goals:
            lines.append(f"GOAL: {goal.name}")

            if goal.description:
                lines.append(f"  MOTIVATION: {goal.description}")

            # Get active projects for this goal
            projects = [p for p in self.repo.data.projects if p.goal_id == goal.id and p.status == "active"]

            if not projects:
                lines.append("  (No active projects)")

            for proj in projects:
                lines.append(f"  PROJECT: {proj.name}")

                if proj.description:
                    lines.append(f"    CONTEXT: {proj.description}")

                _append_items(proj)

            lines.append("")

        # 2. Process Orphaned Projects (Maintenance/Misc)
        orphans = [p for p in self.repo.data.projects if not p.goal_id and p.status == "active"]
        if orphans:
            lines.append("GOAL: Maintenance & Misc (No specific goal)")
            for proj in orphans:
                lines.append(f"  PROJECT: {proj.name}")
                if proj.description:
                    lines.append(f"    CONTEXT: {proj.description}")
                _append_items(proj)

        lines.append("```") # End Code Block
        return "\n".join(lines)

class PlanningService:
    def __init__(self, repo: YamlRepository):
        self.repo = repo

    def get_all_goals(self) -> List[Goal]:
        return self.repo.data.goals

    def create_goal(self, name: str, description: str) -> Goal:
        logger.info(f"Creating new Goal: '{name}'")
        new_goal = Goal(name=name, description=description)
        self.repo.data.goals.append(new_goal)
        self.repo.mark_dirty()
        return new_goal

    def add_manual_item(self, project_id: int, kind: str, name: str, **kwargs) -> None:
        """Manual entry bypassing AI"""
        logger.info(f"Manually adding item '{name}' (kind={kind}) to Project {project_id}")
        project = self.repo.find_project(project_id)
        if not project:
            logger.error(f"Project {project_id} not found for manual item addition.")
            return

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
        else:
            logger.warning(f"Unknown item kind '{kind}' provided.")

    def get_projects_for_goal(self, goal_id: str) -> List[Project]:
        """Get all projects linked to a specific goal"""
        return [p for p in self.repo.data.projects if p.goal_id == goal_id]

    def get_orphaned_projects(self) -> List[Project]:
        """Get all projects not linked to any goal"""
        return [p for p in self.repo.data.projects if p.goal_id is None]

    def add_resource(self, project_id: int, name: str, r_type: ResourceType, store: str = "General") -> None:
        """Add a ResourceItem to a project's unified stream"""
        logger.info(f"Adding resource '{name}' to Project {project_id}")
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        resource_item = ResourceItem(name=name, type=r_type, store=store)
        project.items.append(resource_item)
        self.repo.register_item(project, resource_item)

    def add_reference_item(self, project_id: int, name: str, description: str) -> None:
        """Add a ReferenceItem to a project's unified stream"""
        logger.info(f"Adding reference '{name}' to Project {project_id}")
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        reference_item = ReferenceItem(name=name, content=description)
        project.items.append(reference_item)
        self.repo.register_item(project, reference_item)

    def link_project_to_goal(self, project_id: int, goal_id: Optional[str]) -> None:
        """Link a project to a goal (or unlink if goal_id is None)"""
        logger.info(f"Linking Project {project_id} to Goal {goal_id}")
        project = self.repo.find_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Verify goal exists if provided
        if goal_id is not None:
            goal_exists = any(g.id == goal_id for g in self.repo.data.goals)
            if not goal_exists:
                logger.error(f"Goal {goal_id} not found during linking.")
                raise ValueError(f"Goal {goal_id} not found")
        
        project.goal_id = goal_id
        self.repo.mark_dirty()

    def complete_item(self, item_id: str) -> None:
        """Toggle completion status of an item"""
        item = self.repo.find_item(item_id)
        if not item:
            logger.warning(f"Attempted to complete item {item_id}, but it was not found.")
            return

        logger.info(f"Toggling completion for item '{item.name}' ({item_id})")
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
        if not target_proj:
            logger.warning(f"Move requested for unknown project {project_id}")
            return

        logger.debug(f"Moving Project {project_id} {direction}")

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

    def enrich_project(self, project_id: int, classifier) -> Tuple[int, Dict]:
        """
        Iterates through active items in a project and enriches them using AI.
        Returns: (count_of_enriched_items, debug_data_dict)
        """
        project = self.repo.find_project(project_id)
        if not project: return 0, {}

        # Find Goal Name for context
        goal_name = "No Goal"
        if project.goal_id:
            goal = next((g for g in self.repo.data.goals if g.id == project.goal_id), None)
            if goal: goal_name = goal.name

        count = 0
        last_debug_info = {} # Store debug info from the last AI call

        for item in project.items:
            # Skip if already completed or already has tags/duration (don't overwrite good data)
            if getattr(item, 'is_completed', False) or getattr(item, 'is_acquired', False):
                continue

            # Heuristic: Only enrich if "poor" data (no tags AND unknown duration)
            has_tags = bool(item.tags)
            has_duration = getattr(item, 'duration', 'unknown') != 'unknown'

            if not has_tags and not has_duration:
                try:
                    # We assume classifier.enrich_single_item returns (result, debug_data)
                    # You must ensure TaskClassifier.enrich_single_item is updated too!
                    result, debug_data = classifier.enrich_single_item(item.name, project.name, goal_name)

                    last_debug_info = debug_data

                    # Apply updates
                    item.tags = result.extracted_tags
                    if hasattr(item, 'duration'):
                        item.duration = result.estimated_duration or "unknown"

                    # SAFE UPDATE: Notes
                    if hasattr(item, 'notes'):
                        if not item.notes and result.notes:
                            item.notes = result.notes

                    count += 1
                except Exception as e:
                    print(f"Failed to enrich {item.name}: {e}")

        if count > 0:
            self.repo.mark_dirty()

        return count, last_debug_info

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

        # --- DEBUG LOGGING ---
        if not item:
            logger.warning(f"complete_item: Item {item_id} NOT FOUND in index.")
            return

        logger.debug(f"complete_item: Found item '{item.name}' (Type: {type(item).__name__})")

        # Polymorphic completion
        if isinstance(item, TaskItem):
            item.is_completed = not item.is_completed
            self.repo.mark_dirty()
            logger.info(f"Task '{item.name}' completion toggled to: {item.is_completed}")

        elif isinstance(item, ResourceItem):
            item.is_acquired = not item.is_acquired
            self.repo.mark_dirty()
            logger.info(f"Resource '{item.name}' acquired status toggled to: {item.is_acquired}")

        else:
            logger.warning(f"Item type {type(item)} matched neither TaskItem nor ResourceItem. No action taken.")

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
            logger.info(f"Setting resource '{item.name}' acquired status to {is_acquired}")
            item.is_acquired = is_acquired
            self.repo.mark_dirty()
        else:
            logger.error(f"Item {resource_id} is not a ResourceItem. Cannot toggle status.")
            raise ValueError(f"Item {resource_id} is not a ResourceItem")
