import pytest
from unittest.mock import MagicMock
from services.repository import (
    TriageService, PlanningService, ExecutionService,
    YamlRepository, DraftItem
)
from models.entities import (
    Project, TaskItem, ResourceItem, ReferenceItem, ResourceType
)
# --- CORRECTED IMPORT ---
from models.ai_schemas import ClassificationType, ClassificationResult

# --- FIXTURES ---

@pytest.fixture
def mock_repo():
    """
    Creates a Mock Repository with in-memory data structures.
    """
    repo = MagicMock(spec=YamlRepository)

    # Initialize the data container mock
    repo.data = MagicMock()
    repo.data.inbox_tasks = []
    repo.data.goals = []
    repo.data.projects = []

    # Mock the find methods to work with our in-memory lists
    def find_project_side_effect(pid):
        return next((p for p in repo.data.projects if p.id == pid), None)

    def find_item_side_effect(iid):
        for p in repo.data.projects:
            for item in p.items:
                if item.id == iid:
                    return item
        return None

    repo.find_project.side_effect = find_project_side_effect
    repo.find_item.side_effect = find_item_side_effect

    return repo


# --- TEST: DRAFT ITEM FACTORY ---

def test_draft_to_entity_incubate():
    """Validates that INCUBATE classification creates a Task with 'someday' tag."""
    result = ClassificationResult(
        classification_type=ClassificationType.INCUBATE,
        suggested_project="Unmatched",
        confidence=1.0,
        reasoning="Later",
        refined_text="Learn Guitar",
        extracted_tags=[]
    )
    draft = DraftItem(source_text="Raw Input", classification=result)

    entity = draft.to_entity()

    assert isinstance(entity, TaskItem)
    assert entity.name == "Learn Guitar"
    assert "someday" in entity.tags
    assert entity.notes == "Incubated from Triage"


def test_draft_to_entity_shopping():
    """Validates that SHOPPING classification creates a ResourceItem."""
    result = ClassificationResult(
        classification_type=ClassificationType.SHOPPING,
        suggested_project="Groceries",
        confidence=1.0,
        reasoning="Buy",
        refined_text="Milk",
        extracted_tags=[]
    )
    draft = DraftItem(source_text="Buy Milk", classification=result)

    entity = draft.to_entity()

    assert isinstance(entity, ResourceItem)
    assert entity.name == "Milk"
    assert entity.store == "General"


# --- TEST: TRIAGE SERVICE ---

def test_triage_delete_inbox_item(mock_repo):
    """Validates the 'Trash' functionality."""
    service = TriageService(mock_repo)
    mock_repo.data.inbox_tasks = ["Keep me", "Trash me"]

    service.delete_inbox_item("Trash me")

    assert "Trash me" not in mock_repo.data.inbox_tasks
    assert "Keep me" in mock_repo.data.inbox_tasks
    mock_repo.mark_dirty.assert_called()


def test_triage_apply_draft_to_project(mock_repo):
    """Validates moving a draft into a project."""
    service = TriageService(mock_repo)

    # Setup Project
    proj = Project(id=1, name="Test Project")
    mock_repo.data.projects = [proj]
    mock_repo.find_project_by_name.return_value = proj

    # Setup Draft
    result = ClassificationResult(
        classification_type=ClassificationType.TASK,
        suggested_project="Test Project",
        confidence=1.0,
        reasoning="Test",
        refined_text="New Task"
    )
    draft = DraftItem(source_text="Raw", classification=result)

    # Act
    service.apply_draft(draft)

    # Assert
    assert len(proj.items) == 1
    assert proj.items[0].name == "New Task"
    mock_repo.register_item.assert_called()


# --- TEST: PLANNING SERVICE ---

def test_planning_move_project_ordering(mock_repo):
    """Validates reordering projects (Up/Down)."""
    service = PlanningService(mock_repo)

    # Setup 3 projects in order
    p1 = Project(id=1, name="P1", sort_order=1.0, goal_id="g1")
    p2 = Project(id=2, name="P2", sort_order=2.0, goal_id="g1")
    p3 = Project(id=3, name="P3", sort_order=3.0, goal_id="g1")
    mock_repo.data.projects = [p1, p2, p3]

    # Act: Move P2 UP
    service.move_project(2, "up")

    # Assert: P2 should swap sort_order with P1
    assert p2.sort_order == 1.0
    assert p1.sort_order == 2.0
    mock_repo.mark_dirty.assert_called()


def test_planning_link_project_to_goal(mock_repo):
    """Validates linking a project to a goal."""
    service = PlanningService(mock_repo)

    # Setup
    proj = Project(id=1, name="Orphan", goal_id=None)
    mock_repo.data.projects = [proj]
    mock_repo.data.goals = [MagicMock(id="g1")]  # Mock goal existence check

    # Act
    service.link_project_to_goal(1, "g1")

    # Assert
    assert proj.goal_id == "g1"
    mock_repo.mark_dirty.assert_called()


# --- TEST: EXECUTION SERVICE ---

def test_execution_complete_task_toggle(mock_repo):
    """Validates toggling task completion."""
    service = ExecutionService(mock_repo)

    # Setup
    task = TaskItem(name="Task", is_completed=False)
    proj = Project(id=1, name="P1", items=[task])
    mock_repo.data.projects = [proj]

    # Act 1: Complete
    service.complete_item(task.id)
    assert task.is_completed is True
    mock_repo.mark_dirty.assert_called()

    # Act 2: Un-complete
    service.complete_item(task.id)
    assert task.is_completed is False


def test_execution_complete_resource_toggle(mock_repo):
    """Validates toggling resource acquisition."""
    service = ExecutionService(mock_repo)

    # Setup
    res = ResourceItem(name="Milk", is_acquired=False)
    proj = Project(id=1, name="P1", items=[res])
    mock_repo.data.projects = [proj]

    # Act
    service.complete_item(res.id)

    # Assert
    assert res.is_acquired is True
    mock_repo.mark_dirty.assert_called()