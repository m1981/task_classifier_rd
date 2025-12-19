import pytest
from models.entities import Project, TaskItem, ResourceItem, ReferenceItem
from dataset_io import YamlDatasetLoader
from pathlib import Path
import yaml


def test_polymorphic_project_items():
    """Test that a Project can hold different item types in one list"""
    p = Project(id=1, name="Test Project")

    t1 = TaskItem(name="Fix Bug", tags=["code"])
    r1 = ResourceItem(name="Coffee", store="Starbucks")
    ref1 = ReferenceItem(name="Docs", content="http://docs.com")

    # Add mixed types
    p.items.extend([t1, r1, ref1])

    assert len(p.items) == 3
    assert isinstance(p.items[0], TaskItem)
    assert isinstance(p.items[1], ResourceItem)
    assert isinstance(p.items[2], ReferenceItem)

    # Check discriminator
    assert p.items[0].kind == "task"
    assert p.items[1].kind == "resource"


def test_legacy_migration(tmp_path):
    """Test that the Loader converts legacy 'Bag of Lists' to 'Unified Stream'"""

    # 1. Create a legacy YAML file
    legacy_data = {
        "projects": {
            "kitchen": {
                "id": 10,
                "name": "Kitchen",
                "status": "active",
                # Legacy separate lists
                "tasks": [
                    {"id": "t1", "name": "Paint wall", "is_completed": False}
                ],
                "resources": [
                    {"id": "r1", "name": "White Paint", "type": "to_buy", "store": "Home Depot"}
                ]
            }
        }
    }

    f = tmp_path / "legacy.yaml"
    with open(f, 'w') as file:
        yaml.dump(legacy_data, file)

    # 2. Load it using the new Loader
    loader = YamlDatasetLoader()
    content = loader.load(f)

    # 3. Verify Migration
    project = content.projects[0]
    assert len(project.items) == 2

    # Check that they were converted to the correct classes
    item_1 = project.items[0]
    item_2 = project.items[1]

    assert isinstance(item_1, TaskItem)
    assert item_1.name == "Paint wall"

    assert isinstance(item_2, ResourceItem)
    assert item_2.name == "White Paint"
    assert item_2.store == "Home Depot"


def test_serialization_roundtrip(tmp_path):
    """Test that we can save and reload the new structure"""
    from dataset_io import YamlDatasetSaver
    from models.entities import DatasetContent

    # Create Data
    p = Project(id=1, name="Roundtrip")
    p.items.append(TaskItem(name="Task A"))
    p.items.append(ResourceItem(name="Item B"))

    content = DatasetContent(projects=[p])

    # Save
    saver = YamlDatasetSaver()
    saver.save(tmp_path, content)

    # Load
    loader = YamlDatasetLoader()
    loaded_content = loader.load(tmp_path / "dataset.yaml")

    loaded_proj = loaded_content.projects[0]
    assert len(loaded_proj.items) == 2
    assert loaded_proj.items[0].kind == "task"
    assert loaded_proj.items[1].kind == "resource"