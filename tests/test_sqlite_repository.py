import pytest
from models.entities import ProjectStatus, ResourceType
from services.db_models import DBProject, DBTask, DBTag, DBInboxItem

def test_repo_initialization(in_memory_repo):
    """Verify DB tables are created and mirror is empty."""
    assert in_memory_repo.data.projects == []
    assert in_memory_repo.data.inbox_tasks == []
    assert in_memory_repo.data.goals == []


def test_inbox_operations(in_memory_repo):
    """Verify we can add and remove from inbox via SQL."""
    # 1. Add
    in_memory_repo.add_inbox_item("Buy Milk")

    # Check Mirror
    assert "Buy Milk" in in_memory_repo.data.inbox_tasks

    # Check DB directly (Bypassing Domain Layer to prove persistence)
    item = in_memory_repo.session.query(DBInboxItem).first()
    assert item is not None
    assert item.content == "Buy Milk"

    # 2. Remove
    in_memory_repo.remove_inbox_item("Buy Milk")
    assert "Buy Milk" not in in_memory_repo.data.inbox_tasks
    assert in_memory_repo.session.query(DBInboxItem).count() == 0


def test_project_creation_and_sync(in_memory_repo):
    """
    CRITICAL TEST: Verifies the 'Detached State' fix.
    We modify a domain object, sync it, and ensure DB updates.
    """
    # 1. Create Project
    project = in_memory_repo.create_project("Kitchen Reno")
    assert project.id is not None
    assert project.status == ProjectStatus.ACTIVE

    # 2. Modify Domain Object (Add Task)
    from models.entities import Task
    new_task = Task(name="Paint Walls", tags=["diy"])
    project.tasks.append(new_task)

    # 3. Sync (The method under test)
    in_memory_repo.sync_project(project)

    # 4. Verify DB Persistence
    db_project = in_memory_repo.session.query(DBProject).filter_by(name="Kitchen Reno").first()
    assert len(db_project.tasks) == 1
    assert db_project.tasks[0].name == "Paint Walls"

    # Verify Tags were normalized
    db_tag = in_memory_repo.session.query(DBTag).filter_by(name="diy").first()
    assert db_tag is not None


def test_resource_persistence(in_memory_repo):
    """Verify Resources (Shopping List) are saved correctly."""
    proj = in_memory_repo.create_project("Cooking")

    from models.entities import ProjectResource
    res = ProjectResource(name="Flour", type=ResourceType.TO_BUY, store="Aldi")
    proj.resources.append(res)

    in_memory_repo.sync_project(proj)

    # Reload from DB to verify
    in_memory_repo.session.expire_all()
    db_proj = in_memory_repo.session.query(DBProject).first()
    assert len(db_proj.resources) == 1
    assert db_proj.resources[0].store == "Aldi"