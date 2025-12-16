import pytest
from services.repository import SqliteRepository, TriageService, PlanningService, ExecutionService
from models.entities import ResourceType, ProjectStatus


@pytest.fixture
def services(in_memory_repo):
    """Returns a tuple of all services wired to the same DB."""
    return (
        TriageService(in_memory_repo),
        PlanningService(in_memory_repo),
        ExecutionService(in_memory_repo)
    )


def test_workflow_kitchen_renovation(services, in_memory_repo):
    """
    SCENARIO: The "Kitchen Renovation" Lifecycle
    1. Capture: User dumps ideas into Inbox.
    2. Clarify: User converts an idea into a Project.
    3. Plan: User adds a Goal and links the Project.
    4. Organize: User adds shopping items.
    5. Engage: User goes shopping, then completes the task.
    """
    triage, planning, execution = services

    # --- PHASE 1: CAPTURE ---
    triage.add_to_inbox("Fix the leaky sink")
    triage.add_to_inbox("Buy groceries")  # Distraction

    assert "Fix the leaky sink" in triage.get_inbox_items()

    # --- PHASE 2: CLARIFY (Inbox -> Project) ---
    # User decides "Fix sink" is actually a project called "Kitchen Repair"
    triage.create_project_from_inbox("Fix the leaky sink", "Kitchen Repair")

    # Verify Inbox is cleaner
    assert "Fix the leaky sink" not in triage.get_inbox_items()
    assert "Buy groceries" in triage.get_inbox_items()

    # Verify Project exists
    # Note: We need to find the ID. In a real app, the UI knows the ID.
    # Here we query the repo.
    project = next(p for p in in_memory_repo.data.projects if p.name == "Kitchen Repair")
    assert len(project.tasks) == 1
    assert project.tasks[0].name == "Fix the leaky sink"

    # --- PHASE 3: PLAN (Linking to Goal) ---
    goal = planning.create_goal("Home Maintenance", "Keep house standing")

    # Link Project to Goal (Simulating UI action)
    project.goal_id = goal.id
    in_memory_repo.sync_project(project)

    # Verify Link
    linked_projects = planning.get_projects_for_goal(goal.id)
    assert len(linked_projects) == 1
    assert linked_projects[0].name == "Kitchen Repair"

    # --- PHASE 4: ORGANIZE (Resources) ---
    # User realizes they need a wrench
    planning.add_resource(project.id, "Pipe Wrench", ResourceType.TO_BUY, store="Hardware Store")

    # --- PHASE 5: ENGAGE (Shopping) ---
    # User opens Shopping View
    shopping_list = execution.get_aggregated_shopping_list()
    assert "Hardware Store" in shopping_list

    # User buys the wrench
    resource, proj_name = shopping_list["Hardware Store"][0]
    execution.toggle_resource_status(resource.id, True)

    # Verify it's gone from "To Buy" list
    updated_list = execution.get_aggregated_shopping_list()
    assert "Hardware Store" not in updated_list  # Should be empty now

    # --- PHASE 6: EXECUTION (Doing the work) ---
    # User filters for tasks
    next_actions = execution.get_next_actions()
    task_to_do = next(t for t in next_actions if t.name == "Fix the leaky sink")

    # Complete it
    execution.complete_task(project.id, task_to_do.id)

    # Verify Project Status
    # (Reload project from repo to get fresh state)
    final_project = in_memory_repo.find_project(project.id)
    assert final_project.tasks[0].is_completed is True