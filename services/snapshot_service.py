import json
from dataclasses import asdict
from typing import Dict, Any
from pathlib import Path
from services.repository import SqliteRepository
from models.entities import DatasetContent, Project, Task, Goal, ProjectResource, ReferenceItem, ResourceType, \
    ProjectStatus


class SnapshotService:
    def __init__(self, repo: SqliteRepository):
        self.repo = repo

    def export_to_json(self) -> str:
        """
        Serializes the current DB state to a JSON string.
        Sorted keys ensure deterministic output for diffing.
        """
        # 1. Load full state from DB
        # We force a reload from DB to ensure we capture exactly what's persisted
        content: DatasetContent = self.repo._load_full_state()

        # 2. Convert to Dict
        data = asdict(content)

        # 3. Custom Serializer for Enums and Dates
        def default_serializer(obj):
            if hasattr(obj, 'isoformat'):  # Dates
                return obj.isoformat()
            if hasattr(obj, 'value'):  # Enums
                return obj.value
            return str(obj)

        # 4. Dump to JSON with sorting
        return json.dumps(data, default=default_serializer, indent=2, sort_keys=True)

    def restore_from_json(self, json_str: str):
        """
        Wipes the current DB and re-populates it from JSON.
        """
        data = json.loads(json_str)

        # 1. Clear existing data (Truncate tables)
        # We do this via the session to handle cascades
        from services.db_models import DBProject, DBGoal, DBInboxItem, DBTag, DBTask, DBResource, DBReferenceItem

        # Order matters for Foreign Keys!
        self.repo.session.query(DBTask).delete()
        self.repo.session.query(DBResource).delete()
        self.repo.session.query(DBReferenceItem).delete()
        self.repo.session.query(DBProject).delete()
        self.repo.session.query(DBGoal).delete()
        self.repo.session.query(DBInboxItem).delete()
        self.repo.session.commit()

        # FIX: Clear the in-memory mirror too, so we start fresh
        self.repo.data.projects.clear()
        self.repo.data.goals.clear()
        self.repo.data.inbox_tasks.clear()

        # 2. Re-hydrate Domain Objects
        # Goals
        for g in data.get('goals', []):
            goal = Goal(id=g['id'], name=g['name'], description=g.get('description', ''),
                        status=g.get('status', 'active'))
            self.repo.sync_goal(goal)

        # Projects
        for p in data.get('projects', []):
            # Handle Enums
            try:
                status = ProjectStatus(p.get('status', 'active'))
            except:
                status = ProjectStatus.ACTIVE

            proj = Project(
                id=p['id'], name=p['name'], status=status, goal_id=p.get('goal_id'), tags=p.get('tags', [])
            )

            # Tasks
            for t in p.get('tasks', []):
                task = Task(
                    id=t['id'], name=t['name'], is_completed=t['is_completed'],
                    duration=t.get('duration'), tags=t.get('tags', []), notes=t.get('notes', '')
                )
                proj.tasks.append(task)

            # Resources
            for r in p.get('resources', []):
                try:
                    r_type = ResourceType(r.get('type', 'to_buy'))
                except:
                    r_type = ResourceType.TO_BUY

                res = ProjectResource(
                    id=r['id'], name=r['name'], type=r_type, store=r.get('store'),
                    is_acquired=r.get('is_acquired'), link=r.get('link')
                )
                proj.resources.append(res)

            self.repo.sync_project(proj)

        # Inbox
        for item in data.get('inbox_tasks', []):
            self.repo.add_inbox_item(item)

        # Refresh Mirror
        self.repo.save()