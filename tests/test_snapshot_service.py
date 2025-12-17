import pytest
import json
from services.snapshot_service import SnapshotService
from models.entities import Project, Task, Goal, ProjectResource, ResourceType, ProjectStatus


# --- FIXTURES ---
@pytest.fixture
def snapshot_service(in_memory_repo):
    return SnapshotService(in_memory_repo)


# --- TESTS ---

def test_export_produces_valid_json_structure(snapshot_service, in_memory_repo):
    """
    Validates that export_to_json produces a string that can be parsed back
    and contains the root keys we expect.
    """
    # Arrange: Seed some data
    in_memory_repo.add_inbox_item("Raw Idea")
    in_memory_repo.create_project("Test Project")

    # Act
    json_str = snapshot_service.export_to_json()
    data = json.loads(json_str)

    # Assert
    assert "projects" in data
    assert "goals" in data
    assert "inbox_tasks" in data
    assert isinstance(data["projects"], list)
    assert "Raw Idea" in data["inbox_tasks"]


def test_round_trip_integrity(snapshot_service, in_memory_repo):
    """
    The 'Gold Standard' test.
    1. Create complex state.
    2. Export to JSON.
    3. Wipe DB.
    4. Restore from JSON.
    5. Verify state is identical.
    """
    # 1. Arrange: Create Complex State
    goal = in_memory_repo.create_goal("Health", "Get fit")

    proj = in_memory_repo.create_project("Marathon")
    proj.goal_id = goal.id
    proj.status = ProjectStatus.ON_HOLD  # Non-default enum

    task = Task(name="Run 5k", tags=["cardio"])
    proj.tasks.append(task)

    res = ProjectResource(name="Shoes", type=ResourceType.TO_BUY, store="Nike")
    proj.resources.append(res)

    in_memory_repo.sync_project(proj)
    in_memory_repo.add_inbox_item("Pending Item")

    # 2. Act: Export
    json_snapshot = snapshot_service.export_to_json()

    # 3. Act: Simulate Data Loss / Wipe (by creating a fresh repo or just restoring)
    # The restore_from_json method explicitly wipes, so we trust it to do so.
    snapshot_service.restore_from_json(json_snapshot)

    # 4. Assert: Verify Restoration
    # Check Goal
    goals = in_memory_repo.data.goals
    assert len(goals) == 1
    assert goals[0].name == "Health"

    # Check Project
    projects = in_memory_repo.data.projects
    assert len(projects) == 1
    restored_proj = projects[0]
    assert restored_proj.name == "Marathon"
    assert restored_proj.status == ProjectStatus.ON_HOLD  # Verify Enum restored
    assert restored_proj.goal_id == goal.id  # Verify Link restored

    # Check Deep Nested Items
    assert len(restored_proj.tasks) == 1
    assert restored_proj.tasks[0].name == "Run 5k"
    assert restored_proj.tasks[0].tags == ["cardio"]

    assert len(restored_proj.resources) == 1
    assert restored_proj.resources[0].store == "Nike"
    assert restored_proj.resources[0].type == ResourceType.TO_BUY

    # Check Inbox
    assert "Pending Item" in in_memory_repo.data.inbox_tasks


def test_restore_wipes_existing_data(snapshot_service, in_memory_repo):
    """
    Safety Check: Ensure that restoring a snapshot removes OLD data
    that isn't in the snapshot.
    """
    # Arrange: DB has "Old Project"
    in_memory_repo.create_project("Old Project")

    # Create a snapshot representing a DIFFERENT state (only "New Project")
    new_state_json = json.dumps({
        "projects": [{"id": 99, "name": "New Project", "tasks": [], "resources": []}],
        "goals": [],
        "inbox_tasks": []
    })

    # Act
    snapshot_service.restore_from_json(new_state_json)

    # Assert
    projects = in_memory_repo.data.projects
    project_names = [p.name for p in projects]

    assert "Old Project" not in project_names
    assert "New Project" in project_names
    assert len(projects) == 1


def test_restore_handles_enum_fallbacks(snapshot_service, in_memory_repo):
    """
    Resilience Test: If JSON contains invalid/legacy Enum values,
    the service should fallback to defaults rather than crashing.
    """
    # Arrange: JSON with invalid status/type
    corrupt_json = json.dumps({
        "projects": [{
            "id": 1,
            "name": "Robustness Test",
            "status": "INVALID_STATUS",  # Should default to ACTIVE
            "resources": [{
                "id": "r1", "name": "Item",
                "type": "UNKNOWN_TYPE"  # Should default to TO_BUY
            }]
        }],
        "goals": [],
        "inbox_tasks": []
    })

    # Act
    snapshot_service.restore_from_json(corrupt_json)

    # Assert
    proj = in_memory_repo.data.projects[0]
    assert proj.status == ProjectStatus.ACTIVE
    assert proj.resources[0].type == ResourceType.TO_BUY


def test_restore_handles_missing_optional_fields(snapshot_service, in_memory_repo):
    """
    Compatibility Test: Ensure we can load minimal JSON (e.g. manually edited)
    without crashing on missing optional keys like 'tags' or 'notes'.
    """
    minimal_json = json.dumps({
        "projects": [{
            "id": 1,
            "name": "Minimal",
            # Missing: status, goal_id, tags, tasks, resources
        }],
        "goals": [],
        "inbox_tasks": []
    })

    # Act
    snapshot_service.restore_from_json(minimal_json)

    # Assert
    proj = in_memory_repo.data.projects[0]
    assert proj.name == "Minimal"
    assert proj.status == ProjectStatus.ACTIVE  # Default applied
    assert proj.tags == []  # Default applied
    assert proj.tasks == []  # Default applied