import pytest
from unittest.mock import MagicMock
from services.commands import SaveDatasetCommand
from models.dtos import SaveDatasetRequest, SaveDatasetResponse
from models.entities import DatasetContent


# --- Fixtures ---

@pytest.fixture
def mock_dataset_manager():
    """Mocks the infrastructure layer (saving to disk)"""
    return MagicMock()


@pytest.fixture
def mock_projector():
    """Mocks the data transformation layer"""
    projector = MagicMock()
    # Default behavior: just return the dataset passed in
    projector.project_for_save.side_effect = lambda dataset, req: dataset
    return projector


@pytest.fixture
def command(mock_dataset_manager, mock_projector):
    """The System Under Test (SUT)"""
    return SaveDatasetCommand(mock_dataset_manager, mock_projector)


@pytest.fixture
def sample_content():
    """Dummy data to save"""
    return DatasetContent(projects=[], inbox_tasks=[], goals=[])


# --- Tests ---

def test_save_dataset_validation_failure(command, sample_content):
    """
    Scenario: The request is invalid (e.g., empty name).
    Expected: Returns failure response immediately, does NOT call save.
    """
    # Arrange
    # Create a request that we know will fail validation (empty name)
    invalid_request = SaveDatasetRequest(
        name="",
        source_dataset="old_name",
        projects=[],
        inbox_tasks=[]
    )

    # Act
    response = command.execute(invalid_request, sample_content)

    # Assert
    assert response.success is False
    assert response.error_type == "validation"
    assert "cannot be empty" in response.message

    # Critical: Ensure we didn't try to save to disk
    command.dataset_manager.save_dataset.assert_not_called()


def test_save_dataset_success(command, mock_dataset_manager, sample_content):
    """
    Scenario: Validation passes and DatasetManager saves successfully.
    Expected: Returns success response with dataset name.
    """
    # Arrange
    valid_request = SaveDatasetRequest(
        name="new_dataset",
        source_dataset="old_dataset",
        projects=[],
        inbox_tasks=[]
    )

    # Mock the manager to return a success dict
    mock_dataset_manager.save_dataset.return_value = {
        "success": True,
        "message": "Saved OK"
    }

    # Act
    response = command.execute(valid_request, sample_content)

    # Assert
    assert response.success is True
    assert response.dataset_name == "new_dataset"
    assert response.message == "Saved OK"

    # Verify dependencies were called
    command.projector.project_for_save.assert_called_once()
    mock_dataset_manager.save_dataset.assert_called_once_with("new_dataset", sample_content)


def test_save_dataset_infrastructure_failure(command, mock_dataset_manager, sample_content):
    """
    Scenario: Validation passes, but writing to disk fails (e.g., permission error).
    Expected: Returns failure response based on manager output.
    """
    # Arrange
    valid_request = SaveDatasetRequest(
        name="protected_dataset",
        source_dataset="old",
        projects=[],
        inbox_tasks=[]
    )

    # Mock the manager to return a failure dict
    mock_dataset_manager.save_dataset.return_value = {
        "success": False,
        "error": "Permission denied",
        "type": "permission"
    }

    # Act
    response = command.execute(valid_request, sample_content)

    # Assert
    assert response.success is False
    assert response.error_type == "permission"
    assert response.message == "Permission denied"