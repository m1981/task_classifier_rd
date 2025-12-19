import pytest
from unittest.mock import MagicMock
from services.repository import TriageService, YamlRepository, DraftItem
from models.entities import Project, TaskItem, ResourceItem
from models.ai_schemas import ClassificationResult, ClassificationType


@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=YamlRepository)
    repo.data.inbox_tasks = ["Buy milk"]
    repo.data.projects = [Project(id=1, name="Kitchen")]

    # Mock find methods
    repo.find_project.return_value = repo.data.projects[0]
    repo.find_project_by_name.return_value = repo.data.projects[0]

    return repo


def test_draft_to_entity_conversion():
    """Test that DraftItem creates the correct concrete entity"""
    # 1. Shopping Draft
    res_result = ClassificationResult(
        classification_type=ClassificationType.SHOPPING,
        suggested_project="Kitchen",
        confidence=0.9,
        reasoning="It's milk",
        refined_text="Milk"
    )
    draft_res = DraftItem(source_text="Buy milk", classification=res_result)
    entity_res = draft_res.to_entity()

    assert isinstance(entity_res, ResourceItem)
    assert entity_res.name == "Milk"
    assert entity_res.kind == "resource"

    # 2. Task Draft
    task_result = ClassificationResult(
        classification_type=ClassificationType.TASK,
        suggested_project="Kitchen",
        confidence=0.9,
        reasoning="Action",
        refined_text="Call Bob"
    )
    draft_task = DraftItem(source_text="Call Bob", classification=task_result)
    entity_task = draft_task.to_entity()

    assert isinstance(entity_task, TaskItem)
    assert entity_task.name == "Call Bob"
    assert entity_task.kind == "task"


def test_triage_apply_draft(mock_repo):
    """Test applying a draft commits it to the project"""
    service = TriageService(mock_repo)

    # Setup Draft
    result = ClassificationResult(
        classification_type=ClassificationType.TASK,
        suggested_project="Kitchen",
        confidence=1.0,
        reasoning="Test",
        refined_text="Fix sink"
    )
    draft = DraftItem(source_text="Fix sink", classification=result)

    # Execute
    service.apply_draft(draft)

    # Verify
    project = mock_repo.data.projects[0]
    assert len(project.items) == 1
    assert isinstance(project.items[0], TaskItem)
    assert project.items[0].name == "Fix sink"

    # Verify Repo calls
    mock_repo.register_item.assert_called_once()
    mock_repo.mark_dirty.assert_called()