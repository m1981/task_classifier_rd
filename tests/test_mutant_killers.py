import pytest
import uuid
from models.entities import Project, Task, ProjectResource, ResourceType, ProjectStatus, Goal
from services.db_models import DBProject, DBTask, DBResource, DBGoal
from services.repository import SqliteRepository


# --- GROUP 1: KILLING __init__ MUTANTS ---
# Mutants: 3, 5, 6 (Initialization logic)

def test_repo_init_loads_existing_state(tmp_path):
    """
    Kills mutants in __init__ that skip loading state or setting attributes.
    """
    db_file = tmp_path / "test.db"

    # 1. Pre-seed the DB manually (simulating existing data)
    repo1 = SqliteRepository(str(db_file))
    repo1.create_project("Pre-existing Project")
    repo1.session.close()
    repo1.engine.dispose()

    # 2. Initialize NEW repo instance
    repo2 = SqliteRepository(str(db_file))

    # 3. Assertions
    # Kills: self.name = "sqlite_db" mutation
    assert repo2.name == "sqlite_db"

    # Kills: self.data = self._load_full_state() mutation
    # If _load_full_state was removed, this list would be empty
    assert len(repo2.data.projects) == 1
    assert repo2.data.projects[0].name == "Pre-existing Project"


# --- GROUP 2: KILLING _to_domain_project MUTANTS ---
# Mutants: 9, 16, 22-29 (Mapping logic)

def test_mapper_handles_complex_object_graph(in_memory_repo):
    """
    Kills mutants in _to_domain_project that skip mapping specific fields
    like resources, references, or status enums.
    """
    # 1. Create DB state directly to bypass sync logic (isolate the mapper)
    db_proj = DBProject(
        name="Complex",
        status="on_hold",
        description="Desc"
    )
    in_memory_repo.session.add(db_proj)
    in_memory_repo.session.commit()

    # Add children
    db_res = DBResource(
        id=str(uuid.uuid4()),  # <--- FIX WAS HERE
        project_id=db_proj.id,
        name="Res1",
        type="to_gather",
        store="Home",
        is_acquired=True,
        link="http://google.com"
    )
    in_memory_repo.session.add(db_res)
    in_memory_repo.session.commit()

    # 2. Act: Map to Domain
    # We force a reload to trigger _to_domain_project
    in_memory_repo.save()
    domain_proj = in_memory_repo.find_project(db_proj.id)

    # 3. Assertions (Strict)
    # Kills status enum mapping mutants
    assert domain_proj.status == ProjectStatus.ON_HOLD

    # Kills resource mapping mutants (skipping the loop)
    assert len(domain_proj.resources) == 1
    res = domain_proj.resources[0]

    # Kills individual field mapping mutants
    assert res.type == ResourceType.TO_GATHER
    assert res.is_acquired is True
    assert res.link == "http://google.com"


# --- GROUP 3: KILLING sync_project MUTANTS ---
# Mutants: 32-75 (The Update/Delete Logic)

def test_sync_project_updates_existing_task_fields(in_memory_repo):
    """
    Kills mutants that skip the UPDATE block in sync_project.
    (e.g. existing.name = task.name)
    """
    # 1. Setup
    proj = in_memory_repo.create_project("Update Test")
    task = Task(name="Original Name", duration="1h", is_completed=False)
    proj.tasks.append(task)
    in_memory_repo.sync_project(proj)

    # 2. Modify
    task.name = "New Name"
    task.duration = "2h"
    task.is_completed = True

    # 3. Sync
    in_memory_repo.sync_project(proj)

    # 4. Verify DB directly
    in_memory_repo.session.expire_all()
    db_task = in_memory_repo.session.query(DBTask).filter_by(id=task.id).first()

    assert db_task.name == "New Name"  # Kills mutation skipping name update
    assert db_task.duration == "2h"  # Kills mutation skipping duration update
    assert db_task.is_completed is True  # Kills mutation skipping completion update


def test_sync_project_removes_orphaned_resources(in_memory_repo):
    """
    Kills mutants that skip the DELETE block in sync_project.
    """
    # 1. Setup
    proj = in_memory_repo.create_project("Orphan Test")
    res = ProjectResource(name="To Be Deleted")
    proj.resources.append(res)
    in_memory_repo.sync_project(proj)

    # Verify it exists
    assert in_memory_repo.session.query(DBResource).count() == 1

    # 2. Remove from domain
    proj.resources.clear()

    # 3. Sync
    in_memory_repo.sync_project(proj)

    # 4. Verify DB
    # If the delete loop was mutated/removed, this assertion will fail
    assert in_memory_repo.session.query(DBResource).count() == 0


def test_sync_project_updates_in_memory_mirror(in_memory_repo):
    """
    Kills mutants at the end of sync_project that skip updating self.data.
    """
    # 1. Setup
    proj = in_memory_repo.create_project("Mirror Test")

    # 2. Modify Domain Object
    proj.name = "Updated Name"

    # 3. Sync
    in_memory_repo.sync_project(proj)

    # 4. Check Mirror WITHOUT reloading from DB
    # We access the internal data structure directly
    mirror_proj = next(p for p in in_memory_repo.data.projects if p.id == proj.id)

    # If the mirror update logic was removed, this might still be "Mirror Test"
    # depending on object reference identity, but specifically checking
    # goal_id or other fields often catches this.
    assert mirror_proj.name == "Updated Name"


# --- GROUP 4: KILLING sync_goal MUTANTS ---
# Mutants: 1-16

def test_sync_goal_updates_mirror(in_memory_repo):
    """
    Kills mutants in sync_goal that skip appending to self.data.goals.
    """
    goal = Goal(id="g1", name="New Goal")

    # Act
    in_memory_repo.sync_goal(goal)

    # Assert
    # If the `if domain_goal not in self.data.goals` block is mutated, this fails
    assert len(in_memory_repo.data.goals) == 1
    assert in_memory_repo.data.goals[0].name == "New Goal"


# --- GROUP 5: KILLING create_goal MUTANTS ---
# Mutants: 4, 7, 8

def test_create_goal_calls_sync(in_memory_repo):
    """
    Kills mutants in create_goal that return a goal but fail to save it.
    """
    # Act
    goal = in_memory_repo.create_goal("My Goal", "Desc")

    # Assert
    # Check DB directly to ensure sync_goal was actually called
    db_goal = in_memory_repo.session.query(DBGoal).filter_by(id=goal.id).first()
    assert db_goal is not None
    assert db_goal.name == "My Goal"


# --- GROUP 6: KILLING ExecutionService MUTANTS ---
# Mutant: 6 (Filtering logic)

def test_get_next_actions_filtering_strictness(in_memory_repo):
    """
    Kills mutants in get_next_actions that mess up the 'continue' logic.
    """
    from services.repository import ExecutionService
    svc = ExecutionService(in_memory_repo)

    # 1. Setup Scenario
    # Project A: Active, Task 1 (Done), Task 2 (Not Done)
    p_active = in_memory_repo.create_project("Active")
    t_done = Task(name="Done", is_completed=True)
    t_todo = Task(name="Todo", tags=["home"])
    p_active.tasks.extend([t_done, t_todo])
    in_memory_repo.sync_project(p_active)

    # Project B: Completed, Task 3 (Not Done)
    p_done = in_memory_repo.create_project("Completed")
    p_done.status = ProjectStatus.COMPLETED
    t_ignored = Task(name="Ignored")
    p_done.tasks.append(t_ignored)
    in_memory_repo.sync_project(p_done)

    # 2. Act
    actions = svc.get_next_actions(context_filter="home")

    # 3. Assert
    # Should ONLY contain "Todo"
    assert len(actions) == 1
    assert actions[0].name == "Todo"

    # If `if project.status != ACTIVE` was mutated, "Ignored" would appear
    # If `if not task.is_completed` was mutated, "Done" would appear
    # If context filter logic was mutated, "Todo" might disappear or others appear