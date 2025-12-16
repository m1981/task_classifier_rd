from typing import Optional, List
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload
from services.db_models import Base, DBProject, DBTask, DBResource, DBTag, DBInboxItem, DBReferenceItem, DBGoal
from models.entities import Project, Task, ProjectResource, ResourceType, ProjectStatus, ReferenceItem, Goal, \
    DatasetContent


class SqliteRepository:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # We need a fake 'data' property to satisfy the legacy interface
        # if you haven't refactored the Services to stop using repo.data
        self.data = self._load_full_state()

    def _load_full_state(self) -> DatasetContent:
        """
        Legacy Support: Loads everything into memory.
        WARNING: In a real DB app, we shouldn't do this, but it bridges your migration.
        """
        projects = [self._to_domain_project(p) for p in self.session.query(DBProject).all()]
        goals = [self._to_domain_goal(g) for g in self.session.query(DBGoal).all()]
        inbox = [i.content for i in self.session.query(DBInboxItem).all()]
        return DatasetContent(projects=projects, goals=goals, inbox_tasks=inbox)

    # --- Mappers (DB -> Domain) ---
    def _to_domain_task(self, db_task: DBTask) -> Task:
        return Task(
            id=db_task.id,
            name=db_task.name,
            is_completed=db_task.is_completed,
            tags=[t.name for t in db_task.tags],
            duration=db_task.duration or "unknown",
            notes=db_task.notes or ""
        )

    def _to_domain_project(self, db_proj: DBProject) -> Project:
        try:
            status_enum = ProjectStatus(db_proj.status)
        except ValueError:
            status_enum = ProjectStatus.ACTIVE

        return Project(
            id=db_proj.id,
            name=db_proj.name,
            status=status_enum,
            goal_id=db_proj.goal_id,
            tasks=[self._to_domain_task(t) for t in db_proj.tasks],
            resources=[
                ProjectResource(
                    id=r.id, name=r.name, type=ResourceType(r.type),
                    store=r.store, is_acquired=r.is_acquired, link=r.link
                ) for r in db_proj.resources
            ],
            reference_items=[
                ReferenceItem(id=r.id, name=r.name, description=r.description)
                for r in db_proj.reference_items
            ]
        )

    def _to_domain_goal(self, db_goal: DBGoal) -> Goal:
        return Goal(
            id=db_goal.id,
            name=db_goal.name,
            description=db_goal.description,
            status=db_goal.status
        )

    # --- Persistence Logic (The Hard Part) ---

    def save(self):
        """
        The 'Save All' button.
        In a SQL app, this is dangerous/inefficient.
        Ideally, we save specific entities.
        For migration, we commit the session.
        """
        self.session.commit()
        # Refresh the in-memory mirror
        self.data = self._load_full_state()

    def find_project(self, project_id: int) -> Optional[Project]:
        # We return the object from our in-memory mirror to keep reference consistency
        # with the Services that modify lists.
        return next((p for p in self.data.projects if p.id == project_id), None)

    # --- NEW METHODS: To be called by Services instead of modifying lists directly ---

    def sync_project(self, domain_project: Project):
        """
        Updates the DB record to match the Domain Project.
        This handles the 'Detached State' problem.
        """
        db_proj = self.session.query(DBProject).get(domain_project.id)
        if not db_proj:
            return  # Or raise error

        # 1. Update Fields
        db_proj.name = domain_project.name
        db_proj.status = domain_project.status.value

        # 2. Sync Tasks (Complex: Add/Update/Delete)
        # For simplicity in this migration, we can clear and re-add,
        # OR we assume the Service only Adds.
        # Let's implement a smart merge for Tasks.

        existing_ids = {t.id for t in db_proj.tasks}
        domain_ids = {t.id for t in domain_project.tasks}

        # Add New
        for task in domain_project.tasks:
            if task.id not in existing_ids:
                new_db_task = DBTask(
                    id=task.id,
                    project_id=db_proj.id,
                    name=task.name,
                    is_completed=task.is_completed,
                    duration=task.duration,
                    notes=task.notes
                )
                # Handle Tags
                new_db_task.tags = self._resolve_tags(task.tags)
                self.session.add(new_db_task)
            else:
                # Update Existing
                existing = next(t for t in db_proj.tasks if t.id == task.id)
                existing.is_completed = task.is_completed
                existing.name = task.name
                # Update tags if needed...

        self.session.commit()

    def _resolve_tags(self, tag_names: List[str]) -> List[DBTag]:
        """Finds existing tags or creates new ones"""
        result = []
        for name in tag_names:
            tag = self.session.query(DBTag).filter_by(name=name).first()
            if not tag:
                tag = DBTag(name=name)
                self.session.add(tag)
            result.append(tag)
        return result

    def add_inbox_item(self, text: str):
        item = DBInboxItem(content=text)
        self.session.add(item)
        self.session.commit()
        self.data.inbox_tasks.append(text)  # Keep mirror in sync

    def remove_inbox_item(self, text: str):
        # This is tricky because we don't have IDs in the domain inbox list
        # We delete the oldest matching content
        item = self.session.query(DBInboxItem).filter_by(content=text).first()
        if item:
            self.session.delete(item)
            self.session.commit()
            if text in self.data.inbox_tasks:
                self.data.inbox_tasks.remove(text)