import pytest
from unittest.mock import MagicMock, patch
from services.repository import TriageService, YamlRepository, DraftItem
from models.entities import Project, TaskItem, DatasetContent
from models.ai_schemas import ClassificationResult, ClassificationType


# --- FIXTURES ---

@pytest.fixture
def mock_dataset_manager():
    """Mocks the file I/O layer"""
    dm = MagicMock()
    # Default load returns empty structure
    dm.load_dataset.return_value = DatasetContent()
    return dm


@pytest.fixture
def repo(mock_dataset_manager):
    """Real Repository instance with mocked storage"""
    return YamlRepository(mock_dataset_manager, "test_db")


@pytest.fixture
def triage_service(repo):
    return TriageService(repo)


# --- TESTS: YamlRepository ---

def test_repo_initialization_loads_data(mock_dataset_manager):
    """Verify repo calls loader on init"""
    YamlRepository(mock_dataset_manager, "my_db")
    mock_dataset_manager.load_dataset.assert_called_once_with("my_db")


def test_repo_dirty_flag_logic(repo):
    """Verify dirty flag state transitions"""
    assert repo.is_dirty is False

    repo.mark_dirty()
    assert repo.is_dirty is True

    repo.save()
    assert repo.is_dirty is False
    repo.dm.save_dataset.assert_called_once()


def test_repo_indexing_and_retrieval(repo):
    """Verify O(1) lookup index works"""
    # Setup Data
    task = TaskItem(name="Find Me")
    proj = Project(id=1, name="P1", items=[task])
    repo.data.projects = [proj]

    # Act: Rebuild index (usually happens on init or register)
    repo._rebuild_index()

    # Assert
    found_item = repo.find_item(task.id)
    assert found_item == task
    assert repo.find_item("non-existent") is None


def test_repo_find_project_helpers(repo):
    """Verify project lookup helpers"""
    p1 = Project(id=10, name="Alpha")
    p2 = Project(id=20, name="Beta")
    repo.data.projects = [p1, p2]

    assert repo.find_project(10) == p1
    assert repo.find_project(99) is None

    assert repo.find_project_by_name("Beta") == p2
    assert repo.find_project_by_name("Gamma") is None


# --- TESTS: TriageService ---

def test_skip_inbox_item_success(triage_service, repo):
    """
    Scenario: User skips an item.
    Expected: Item moves from front to back of list.
    """
    repo.data.inbox_tasks = ["Item A", "Item B", "Item C"]

    triage_service.skip_inbox_item("Item A")

    assert repo.data.inbox_tasks == ["Item B", "Item C", "Item A"]
    assert repo.is_dirty is True


def test_skip_inbox_item_not_found(triage_service, repo):
    """
    Scenario: User tries to skip item not in inbox (race condition).
    Expected: No change, no error.
    """
    repo.data.inbox_tasks = ["Item A"]

    triage_service.skip_inbox_item("Ghost Item")

    assert repo.data.inbox_tasks == ["Item A"]


def test_create_project_from_draft_success(triage_service, repo):
    """
    Scenario: AI suggests New Project.
    Expected: New Project created, Item added as Task, Inbox cleared.
    """
    # Setup
    repo.data.inbox_tasks = ["Build App"]
    repo.data.projects = [Project(id=1, name="Existing")]

    result = ClassificationResult(
        classification_type=ClassificationType.NEW_PROJECT,
        suggested_project="Unmatched",
        confidence=1.0,
        reasoning="Big goal",
        refined_text="Build App MVP",
        suggested_new_project_name="App Project"
    )
    draft = DraftItem(source_text="Build App", classification=result)

    # Act
    triage_service.create_project_from_draft(draft, "App Project")

    # Assert
    # 1. Project Created
    new_proj = repo.find_project(2)  # ID should auto-increment
    assert new_proj is not None
    assert new_proj.name == "App Project"

    # 2. Item Added
    assert len(new_proj.items) == 1
    assert new_proj.items[0].name == "Build App MVP"

    # 3. Inbox Cleared
    assert "Build App" not in repo.data.inbox_tasks


def test_create_project_from_inbox_manual_success(triage_service, repo):
    """
    Scenario: Manual 'Create Project' from UI.
    Expected: New Project created, Item added as Task.
    """
    repo.data.inbox_tasks = ["Raw Idea"]
    repo.data.projects = []

    triage_service.create_project_from_inbox("Raw Idea", "Manual Project")

    new_proj = repo.find_project(1)
    assert new_proj.name == "Manual Project"
    assert new_proj.items[0].name == "Raw Idea"
    assert "Raw Idea" not in repo.data.inbox_tasks


def test_move_inbox_item_to_project_success(triage_service, repo):
    """
    Scenario: Manual assignment to existing project.
    Expected: Item becomes Task in target project.
    """
    repo.data.inbox_tasks = ["Buy Milk"]
    target_proj = Project(id=1, name="Groceries")
    repo.data.projects = [target_proj]

    triage_service.move_inbox_item_to_project("Buy Milk", 1, ["tag1"])

    assert len(target_proj.items) == 1
    item = target_proj.items[0]
    assert item.name == "Buy Milk"
    assert item.tags == ["tag1"]
    assert "Buy Milk" not in repo.data.inbox_tasks


def test_move_inbox_item_to_project_invalid_id(triage_service, repo):
    """
    Scenario: Target project ID does not exist.
    Expected: ValueError raised.
    """
    repo.data.inbox_tasks = ["Task"]
    repo.data.projects = []

    with pytest.raises(ValueError, match="Project 999 not found"):
        triage_service.move_inbox_item_to_project("Task", 999, [])


def test_apply_draft_invalid_project(triage_service, repo):
    """
    Scenario: Applying draft to non-existent project.
    Expected: ValueError raised.
    """
    result = ClassificationResult(
        classification_type=ClassificationType.TASK,
        suggested_project="Ghost Project",
        confidence=1.0,
        reasoning="test",
        refined_text="Task"
    )
    draft = DraftItem("Task", result)

    with pytest.raises(ValueError, match="Target project not found"):
        triage_service.apply_draft(draft)