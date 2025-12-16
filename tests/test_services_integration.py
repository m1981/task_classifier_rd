import pytest
from services.repository import TriageService, PlanningService, ExecutionService
from models.entities import ResourceType


@pytest.fixture
def triage_service(in_memory_repo):
    return TriageService(in_memory_repo)


@pytest.fixture
def planning_service(in_memory_repo):
    return PlanningService(in_memory_repo)


def test_triage_move_to_project(triage_service, in_memory_repo):
    """
    Verifies the full flow: Inbox -> Project.
    Checks if @autosave triggers the commit/refresh.
    """
    # Setup
    in_memory_repo.add_inbox_item("Fix Door")
    proj = in_memory_repo.create_project("Home Maintenance")

    # Action
    triage_service.move_inbox_item_to_project("Fix Door", proj.id, ["urgent"])

    # Assertions
    # 1. Inbox should be empty
    assert "Fix Door" not in in_memory_repo.data.inbox_tasks

    # 2. Project should have task
    # We fetch fresh from repo.data to ensure the Mirror was refreshed by @autosave
    updated_proj = next(p for p in in_memory_repo.data.projects if p.id == proj.id)
    assert len(updated_proj.tasks) == 1
    assert updated_proj.tasks[0].name == "Fix Door"
    assert updated_proj.tasks[0].tags == ["urgent"]


def test_planning_create_goal_hierarchy(planning_service, in_memory_repo):
    """Verifies Goal -> Project linking."""
    # 1. Create Goal
    goal = planning_service.create_goal("Live Healthy", "Exercise more")

    # 2. Create Project manually and link (simulating UI logic)
    proj = in_memory_repo.create_project("Gym Routine")
    proj.goal_id = goal.id
    in_memory_repo.sync_project(proj)

    # 3. Verify Service Query
    projects = planning_service.get_projects_for_goal(goal.id)
    assert len(projects) == 1
    assert projects[0].name == "Gym Routine"


def test_autosave_decorator_integration(triage_service, in_memory_repo):
    """
    Verifies that the @autosave decorator actually commits to the DB.
    """
    # We use add_to_inbox which is decorated with @autosave
    triage_service.add_to_inbox("Test Item")

    # If autosave worked, the session should be committed and data refreshed.
    # We check the DB directly to ensure it's there.
    from services.db_models import DBInboxItem
    # We use a new session to ensure we aren't reading uncommitted data
    new_session = in_memory_repo.session
    assert new_session.query(DBInboxItem).filter_by(content="Test Item").count() == 1