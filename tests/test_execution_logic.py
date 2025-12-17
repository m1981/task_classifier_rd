import pytest
from services.repository import ExecutionService
from models.entities import ProjectStatus, ResourceType


@pytest.fixture
def exec_service(in_memory_repo):
    return ExecutionService(in_memory_repo)


def test_next_actions_iterates_all_projects(in_memory_repo, exec_service):
    """
    Kills Mutant: 'continue' changed to 'break' in get_next_actions loop.
    If the loop breaks on the first non-active project, it won't find the second active one.
    """
    # Project 1: Completed (Should be skipped)
    p1 = in_memory_repo.create_project("Done Proj")
    p1.status = ProjectStatus.COMPLETED
    in_memory_repo.sync_project(p1)

    # Project 2: Active (Should be found)
    p2 = in_memory_repo.create_project("Active Proj")
    from models.entities import Task
    t2 = Task(name="Find Me")
    p2.tasks.append(t2)
    in_memory_repo.sync_project(p2)

    # Act
    actions = exec_service.get_next_actions()

    # Assert
    task_names = [t.name for t in actions]
    assert "Find Me" in task_names


def test_shopping_list_default_store(in_memory_repo, exec_service):
    """
    Kills Mutant: store="General" changed to "XXGeneralXX" or lowercase.
    """
    p = in_memory_repo.create_project("Shop Proj")
    from models.entities import ProjectResource
    # Resource with empty store -> Should default to "General"
    r = ProjectResource(name="Milk", type=ResourceType.TO_BUY, store="")
    p.resources.append(r)
    in_memory_repo.sync_project(p)

    # Act
    shopping = exec_service.get_aggregated_shopping_list()

    # Assert
    assert "General" in shopping
    assert shopping["General"][0][0].name == "Milk"


def test_shopping_list_iterates_all(in_memory_repo, exec_service):
    """
    Kills Mutant: 'continue' changed to 'break' in shopping list loop.
    """
    # P1: Completed
    p1 = in_memory_repo.create_project("P1")
    p1.status = ProjectStatus.COMPLETED
    in_memory_repo.sync_project(p1)

    # P2: Active with item
    p2 = in_memory_repo.create_project("P2")
    from models.entities import ProjectResource
    r = ProjectResource(name="Bread", type=ResourceType.TO_BUY)
    p2.resources.append(r)
    in_memory_repo.sync_project(p2)

    shopping = exec_service.get_aggregated_shopping_list()
    assert "General" in shopping  # If loop broke on P1, this would fail