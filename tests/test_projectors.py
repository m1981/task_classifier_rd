import pytest
from services.projectors import DatasetProjector
from models.entities import DatasetContent, Project
from models.dtos import SaveDatasetRequest


# --- Fixtures ---

@pytest.fixture
def sample_dataset():
    """Creates a populated dataset for testing"""
    return DatasetContent(
        projects=[
            Project(id=1, name="Kitchen Reno"),
            Project(id=2, name="Learn Python")
        ],
        inbox_tasks=["Buy Milk", "Call Mom"],
        goals=[]
    )


# --- Tests ---

def test_from_ui_state_maps_correctly(sample_dataset):
    """
    Scenario: Converting the current application state into a Save Request DTO.
    Expected:
    1. Target name and Source name are preserved.
    2. Project names are extracted into a list of strings.
    3. Inbox tasks are copied over.
    """
    # Arrange
    target_name = "my_new_backup"
    source_name = "original_data"

    # Act
    request = DatasetProjector.from_ui_state(sample_dataset, target_name, source_name)

    # Assert
    assert isinstance(request, SaveDatasetRequest)
    assert request.name == target_name
    assert request.source_dataset == source_name

    # Verify data mapping
    assert request.inbox_tasks == ["Buy Milk", "Call Mom"]
    # Check that project objects were converted to a list of names
    assert request.projects == ["Kitchen Reno", "Learn Python"]


def test_project_for_save_returns_dataset_as_is(sample_dataset):
    """
    Scenario: Preparing the dataset for saving.
    Current Logic: The method currently just passes the dataset through.
    Expected: The returned object is identical to the input object.
    """
    # Arrange
    dummy_request = SaveDatasetRequest(
        name="test",
        source_dataset="test",
        projects=[],
        inbox_tasks=[]
    )

    # Act
    result = DatasetProjector.project_for_save(sample_dataset, dummy_request)

    # Assert
    assert result == sample_dataset
    assert result is sample_dataset  # Verify it's the exact same instance