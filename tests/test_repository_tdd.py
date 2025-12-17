import pytest
import tempfile
import os
from services.repository import SqliteRepository
from models.entities import Project, Task, ProjectStatus


# --- FIXTURE: Disposable Real DB ---
@pytest.fixture
def repo():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repo = SqliteRepository(path)
    yield repo
    repo.session.close()
    repo.engine.dispose()
    if os.path.exists(path):
        os.unlink(path)


# --- TDD CYCLE 1: Basic Persistence ---
def test_create_and_retrieve_project(repo):
    """
    GIVEN a new project "Alpha"
    WHEN it is created via the repository
    THEN it should be retrievable by ID
    AND it should have a generated ID
    """
    # Act
    proj = repo.create_project("Alpha")

    # Assert
    assert proj.id is not None
    assert isinstance(proj.id, int)

    # Verify Persistence (Reload from DB)
    repo.session.expire_all()
    retrieved = repo.find_project(proj.id)
    assert retrieved.name == "Alpha"


# --- TDD CYCLE 2: Complex Object Graph (Sync) ---
def test_sync_project_updates_children(repo):
    """
    GIVEN an existing project
    WHEN we add tasks and resources in the Domain Object
    AND we call sync_project()
    THEN the DB should reflect these new children
    """
    # Arrange
    proj = repo.create_project("Renovation")

    # Act
    from models.entities import Task, ProjectResource, ResourceType
    new_task = Task(name="Paint Walls")
    new_res = ProjectResource(name="Paint", type=ResourceType.TO_BUY)

    proj.tasks.append(new_task)
    proj.resources.append(new_res)

    repo.sync_project(proj)

    # Assert (Check DB directly via Session to bypass cache)
    from services.db_models import DBTask, DBResource
    db_task = repo.session.query(DBTask).filter_by(name="Paint Walls").first()
    db_res = repo.session.query(DBResource).filter_by(name="Paint").first()

    assert db_task is not None
    assert db_task.project_id == proj.id
    assert db_res is not None
    assert db_res.type == "to_buy"  # Enum serialization check


# --- TDD CYCLE 3: Orphan Removal ---
def test_sync_removes_deleted_tasks(repo):
    """
    GIVEN a project with a task
    WHEN the task is removed from the Domain Object list
    AND sync_project() is called
    THEN the task should be deleted from the DB (Cascade)
    """
    # Arrange
    proj = repo.create_project("Cleanup")
    task = Task(name="Trash")
    proj.tasks.append(task)
    repo.sync_project(proj)

    # Act
    proj.tasks.clear()  # Remove from memory
    repo.sync_project(proj)

    # Assert
    from services.db_models import DBTask
    count = repo.session.query(DBTask).count()
    assert count == 0