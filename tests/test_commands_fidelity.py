import pytest
from services.commands import SaveDatasetCommand
from models.dtos import SaveDatasetRequest
from unittest.mock import MagicMock


def test_save_command_returns_correct_message():
    """
    Kills Mutant: message=result.get("message", None)
    """
    # Setup Mocks
    mock_dm = MagicMock()
    mock_dm.save_dataset.return_value = {"success": True, "message": "Saved OK"}
    mock_proj = MagicMock()

    cmd = SaveDatasetCommand(mock_dm, mock_proj)
    req = SaveDatasetRequest(name="test", source_dataset="src", projects=[], inbox_tasks=[])

    # Act
    response = cmd.execute(req, None)

    # Assert
    assert response.success is True
    assert response.message == "Saved OK"  # If mutant survived, this might be None or empty