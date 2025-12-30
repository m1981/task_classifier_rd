import pytest
from unittest.mock import MagicMock
from services.repository import PlanningService, ExecutionService, TriageService, YamlRepository, DraftItem

# --- CORRECTED IMPORTS ---
from models.entities import Project, TaskItem, ResourceItem
from models.ai_schemas import ClassificationType, ClassificationResult

# --- FIXTURES ---
@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=YamlRepository)

    # --- FIX: Configure the 'data' attribute as a Mock first ---
    repo.data = MagicMock()

    # Setup in-memory data
    p1 = Project(id=1, name="P1", sort_order=1.0, goal_id="g1")
    p2 = Project(id=2, name="P2", sort_order=2.0, goal_id="g1")
    p3 = Project(id=3, name="P3", sort_order=3.0, goal_id="g2")

    repo.data.projects = [p1, p2, p3]
    repo.data.inbox_tasks = ["Buy milk"]

    # Mock find methods
    repo.find_project.side_effect = lambda pid: next((p for p in repo.data.projects if p.id == pid), None)
    repo.find_item.return_value = None  # Default

    return repo


# --- PLANNING SERVICE TESTS ---

def test_move_project_up(mock_repo):
    service = PlanningService(mock_repo)

    # Act: Move P2 (index 1) UP
    service.move_project(2, "up")

    # Assert: P2 should swap sort_order with P1
    p1 = mock_repo.data.projects[0]
    p2 = mock_repo.data.projects[1]

    # Note: The list order in mock_repo might not change immediately unless we sort it,
    # but the sort_order values MUST swap.
    assert p2.sort_order == 1.0  # P2 took P1's spot
    assert p1.sort_order == 2.0  # P1 moved down
    mock_repo.mark_dirty.assert_called()


def test_move_project_down_boundary(mock_repo):
    service = PlanningService(mock_repo)

    # Act: Try to move P2 (index 1) DOWN (it is the last in goal "g1")
    # P3 is in "g2", so P2 shouldn't swap with P3.
    service.move_project(2, "down")

    # Assert: No change expected
    p2 = mock_repo.data.projects[1]
    assert p2.sort_order == 2.0
    # mark_dirty might NOT be called if logic detects no move possible,
    # or called redundantly. Checking state is more important.


# --- EXECUTION SERVICE TESTS ---

def test_complete_task_toggles_state(mock_repo):
    service = ExecutionService(mock_repo)

    # Setup a task
    task = TaskItem(name="Test Task", is_completed=False)
    mock_repo.find_item.return_value = task

    # Act
    service.complete_item(task.id)

    # Assert
    assert task.is_completed is True
    mock_repo.mark_dirty.assert_called()

    # Act Again (Toggle back)
    service.complete_item(task.id)
    assert task.is_completed is False


def test_complete_resource_toggles_acquired(mock_repo):
    service = ExecutionService(mock_repo)

    # Setup a resource
    res = ResourceItem(name="Milk", is_acquired=False)
    mock_repo.find_item.return_value = res

    # Act
    service.complete_item(res.id)

    # Assert
    assert res.is_acquired is True


# --- TRIAGE SERVICE TESTS ---

def test_create_draft_factory_logic(mock_repo):
    service = TriageService(mock_repo)

    # Scenario: AI suggests a Task
    result = ClassificationResult(
        classification_type=ClassificationType.TASK,
        suggested_project="P1",
        confidence=1.0,
        reasoning="test",
        refined_text="Refined Task",
        estimated_duration="15min"
    )

    # Act
    draft = service.create_draft("Raw Input", result)
    entity = draft.to_entity()

    # Assert
    assert isinstance(entity, TaskItem)
    assert entity.name == "Refined Task"
    assert entity.duration == "15min"


def test_delete_inbox_item(mock_repo):
    service = TriageService(mock_repo)

    # Act
    service.delete_inbox_item("Buy milk")

    # Assert
    assert "Buy milk" not in mock_repo.data.inbox_tasks
    mock_repo.mark_dirty.assert_called()