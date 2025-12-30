import pytest
import yaml
from pathlib import Path
from dataset_io import YamlDatasetLoader, YamlDatasetSaver
from models.entities import DatasetContent, Project, ProjectStatus, TaskItem
import logging

# --- FIXTURES ---

@pytest.fixture
def loader():
    return YamlDatasetLoader()


@pytest.fixture
def saver():
    return YamlDatasetSaver()


@pytest.fixture
def yaml_file(tmp_path):
    """Returns a path to a temporary YAML file"""
    return tmp_path / "dataset.yaml"


# --- TESTS ---

def test_load_project_with_explicit_sort_order(loader, yaml_file):
    """
    Validates that 'sort_order' is correctly loaded and doesn't cause
    argument collision errors.
    """
    data = {
        "projects": [
            {
                "id": 1,
                "name": "Test Project",
                "sort_order": 5.5,
                "status": "active",
                "items": []
            }
        ]
    }

    with open(yaml_file, 'w') as f:
        yaml.dump(data, f)

    # Act
    content = loader.load(yaml_file)
    project = content.projects[0]

    # Assert
    assert project.id == 1
    assert project.sort_order == 5.5

def test_load_project_defaults_sort_order_to_id(loader, yaml_file):
    """
    Validates that if 'sort_order' is missing in YAML,
    it defaults to the Project ID (float).
    """
    data = {
        "projects": [
            {
                "id": 10,
                "name": "Legacy Project",
                # No sort_order provided
                "status": "active",
                "items": []
            }
        ]
    }

    with open(yaml_file, 'w') as f:
        yaml.dump(data, f)

    # Act
    content = loader.load(yaml_file)
    project = content.projects[0]

    # Assert
    assert project.id == 10
    assert project.sort_order == 10.0  # Defaulted to ID

def test_load_unified_stream_items(loader, yaml_file):
    """
    Validates that items in the 'items' list are correctly parsed
    into their polymorphic types based on 'kind'.
    """
    data = {
        "projects": [
            {
                "id": 1,
                "name": "Unified Project",
                "items": [
                    {
                        "kind": "task",
                        "id": "t1",
                        "name": "Task 1",
                        "is_completed": False
                    },
                    {
                        "kind": "resource",
                        "id": "r1",
                        "name": "Milk",
                        "type": "to_buy"
                    }
                ]
            }
        ]
    }

    with open(yaml_file, 'w') as f:
        yaml.dump(data, f)

    # Act
    content = loader.load(yaml_file)
    project = content.projects[0]

    # Assert
    assert len(project.items) == 2
    assert project.items[0].kind == "task"
    assert project.items[0].name == "Task 1"
    assert project.items[1].kind == "resource"
    assert project.items[1].name == "Milk"

def test_save_sorts_projects_correctly(saver, tmp_path):
    """
    Validates that saving the dataset reorders projects based on
    Goal ID and Sort Order.
    """
    # Arrange: Create projects out of order
    p1 = Project(id=1, name="Second", sort_order=2.0, goal_id="g1")
    p2 = Project(id=2, name="First", sort_order=1.0, goal_id="g1")
    p3 = Project(id=3, name="Orphaned", sort_order=5.0, goal_id=None)

    content = DatasetContent(
        projects=[p1, p3, p2],  # Random order in memory
        goals=[],
        inbox_tasks=[]
    )

    # Act
    saver.save(tmp_path, content)

    # Assert: Read the file back raw to check order
    saved_file = tmp_path / "dataset.yaml"
    with open(saved_file, 'r') as f:
        saved_data = yaml.safe_load(f)

    saved_projects = saved_data['projects']

    # Expected order:
    # 1. Orphaned (goal_id=None sorts first)
    # 2. Goal g1, sort_order 1.0
    # 3. Goal g1, sort_order 2.0

    assert saved_projects[0]['name'] == "Orphaned"
    assert saved_projects[1]['name'] == "First"
    assert saved_projects[2]['name'] == "Second"

def test_load_file_not_found(loader, tmp_path):
    """Validates error handling for missing files."""
    missing_file = tmp_path / "non_existent.yaml"

    with pytest.raises(FileNotFoundError):
        loader.load(missing_file)


def test_load_invalid_yaml(loader, yaml_file):
    """Validates error handling for corrupted files."""
    with open(yaml_file, 'w') as f:
        f.write("This is : not : valid : yaml")

    with pytest.raises(Exception):
        loader.load(yaml_file)

def test_load_raises_and_logs_on_invalid_project_data(loader, yaml_file, caplog):
    """
    Validates that if a single project is malformed (e.g. missing required 'name'),
    the loader logs the specific error index and re-raises the exception.
    """
    # Arrange: Create YAML with one valid and one invalid project
    data = {
        "projects": [
            {
                "id": 1,
                "name": "Valid Project",
                "items": []
            },
            {
                "id": 2,
                # Missing 'name' field, which is required by Pydantic model
                "items": []
            }
        ]
    }

    with open(yaml_file, 'w') as f:
        yaml.dump(data, f)

    # Act & Assert
    # We expect a validation error (or generic Exception depending on Pydantic version)
    with pytest.raises(Exception):
        loader.load(yaml_file)

    # Verify Logging
    # We expect an error log for index 1 (the second project)
    # caplog captures all logs during the test
    assert "Failed to parse project index 1" in caplog.text
    assert "Unknown" in caplog.text # Since name is missing, it defaults to 'Unknown' in the log message