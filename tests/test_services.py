import pytest
from unittest.mock import MagicMock
from services.repository import TriageService, YamlRepository
from models.entities import DatasetContent, Project, Task


# --- Fixtures ---
@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=YamlRepository)
    # Setup in-memory data structure
    repo.data = DatasetContent(
        projects=[
            Project(id=1, name="Kitchen", tasks=[])
        ],
        inbox_tasks=["Buy Milk", "Fix Door"],
        goals=[]
    )
    # Mock find_project to return the project from our list
    repo.find_project.side_effect = lambda pid: next((p for p in repo.data.projects if p.id == pid), None)
    return repo


@pytest.fixture
def triage_service(mock_repo):
    return TriageService(mock_repo)


# --- Tests ---

def test_get_inbox_items(triage_service, mock_repo):
    items = triage_service.get_inbox_items()
    assert len(items) == 2
    assert "Buy Milk" in items


def test_add_to_inbox(triage_service, mock_repo):
    triage_service.add_to_inbox("New Idea")
    assert "New Idea" in mock_repo.data.inbox_tasks
    mock_repo.save.assert_called_once()


def test_move_inbox_item_to_project(triage_service, mock_repo):
    # Arrange
    task_text = "Buy Milk"
    project_id = 1
    tags = ["errand"]

    # Act
    triage_service.move_inbox_item_to_project(task_text, project_id, tags)

    # Assert
    # 1. Check it was removed from inbox
    assert task_text not in mock_repo.data.inbox_tasks

    # 2. Check it was added to project
    project = mock_repo.data.projects[0]
    assert len(project.tasks) == 1
    assert project.tasks[0].name == task_text
    assert project.tasks[0].tags == ["errand"]

    # 3. Check save was called
    mock_repo.save.assert_called()


def test_skip_inbox_item(triage_service, mock_repo):
    # Arrange: Inbox is ["Buy Milk", "Fix Door"]
    first_item = "Buy Milk"

    # Act
    triage_service.skip_inbox_item(first_item)

    # Assert: "Buy Milk" should now be at the end
    assert mock_repo.data.inbox_tasks[-1] == first_item
    assert len(mock_repo.data.inbox_tasks) == 2