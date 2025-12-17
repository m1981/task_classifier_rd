import pytest
from models.entities import Project, Task, ProjectResource, ResourceType, ProjectStatus, Goal
from services.db_models import DBProject, DBTask


def test_repo_attributes(in_memory_repo):
    """
    Kills Mutant: self.name = "XXsqlite_dbXX"
    """
    assert in_memory_repo.name == "sqlite_db"


def test_mapper_full_fidelity(in_memory_repo):
    """
    Kills Mutants:
    - _to_domain_task: duration=None, notes=None
    - _to_domain_project: status=None, goal_id=None
    """
    # 1. Setup Complex Data
    goal = in_memory_repo.create_goal("Life", "Big things")
    proj = in_memory_repo.create_project("Complex Project")

    # Set specific values that mutants try to wipe out
    proj.status = ProjectStatus.ON_HOLD
    proj.goal_id = goal.id

    task = Task(
        name="Detailed Task",
        duration="45m",
        notes="Do not forget",
        tags=["urgent"]
    )
    proj.tasks.append(task)

    # 2. Sync
    in_memory_repo.sync_project(proj)

    # 3. Reload from fresh session (bypass cache)
    in_memory_repo.session.expire_all()
    loaded_proj = in_memory_repo.find_project(proj.id)

    # 4. Strict Assertions
    assert loaded_proj.status == ProjectStatus.ON_HOLD  # Kills status=None
    assert loaded_proj.goal_id == goal.id  # Kills goal_id=None

    loaded_task = loaded_proj.tasks[0]
    assert loaded_task.duration == "45m"  # Kills duration=None
    assert loaded_task.notes == "Do not forget"  # Kills notes=None


def test_sync_project_updates_existing_fields(in_memory_repo):
    """
    Kills Mutants: sync_project setting fields to None on update
    """
    # 1. Create
    proj = in_memory_repo.create_project("Update Me")
    task = Task(name="Task A", duration="1h", notes="Note A")
    proj.tasks.append(task)
    in_memory_repo.sync_project(proj)

    # 2. Update
    task.duration = "2h"
    task.notes = "Note B"
    in_memory_repo.sync_project(proj)

    # 3. Verify DB
    in_memory_repo.session.expire_all()
    db_task = in_memory_repo.session.query(DBTask).filter_by(id=task.id).first()

    assert db_task.duration == "2h"  # Kills existing_db_task.duration = None
    assert db_task.notes == "Note B"  # Kills existing_db_task.notes = None