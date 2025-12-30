import pytest
import shutil
from pathlib import Path
from services import DatasetManager, PromptBuilder, TaskClassifier
from services.repository import YamlRepository, TriageService, PlanningService, ExecutionService
from services.analytics_service import AnalyticsService
from models.entities import TaskItem, ReferenceItem, ResourceItem, Project
from tests.mocks import MockAIClient
from models.dtos import SingleTaskClassificationRequest


# --- FIXTURES ---

@pytest.fixture
def e2e_env(tmp_path):
    """
    Sets up a clean environment with a fresh YAML file and Services.
    """
    # 1. Setup Data Directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # 2. Create a blank dataset
    yaml_content = """
    goals: []
    projects:
      - id: 1
        name: Groceries
        status: active
        items: []
    inbox_tasks: []
    """
    (data_dir / "test_db").mkdir()
    (data_dir / "test_db" / "dataset.yaml").write_text(yaml_content, encoding='utf-8')

    # 3. Initialize Infrastructure
    dm = DatasetManager(base_path=data_dir)
    repo = YamlRepository(dm, "test_db")

    # 4. Inject Mock AI
    mock_client = MockAIClient()
    prompt_builder = PromptBuilder()
    classifier = TaskClassifier(mock_client, prompt_builder)

    # 5. Initialize Services
    return {
        "repo": repo,
        "triage": TriageService(repo),
        "planning": PlanningService(repo),
        "exec": ExecutionService(repo),
        "analytics": AnalyticsService(repo, mock_client, prompt_builder),
        "classifier": classifier
    }


# --- THE TESTS ---

def test_full_gtd_lifecycle_happy_path(e2e_env):
    """
    Scenario:
    1. User captures "Buy milk".
    2. AI classifies it as Shopping for "Groceries".
    3. User confirms.
    4. User checks "Groceries" list.
    5. User marks it done.
    6. User saves to disk.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]
    execution = e2e_env["exec"]

    # --- STEP 1: CAPTURE ---
    triage.add_to_inbox("Buy milk")
    assert "Buy milk" in repo.data.inbox_tasks
    assert repo.is_dirty is True

    # --- STEP 2: AI ANALYSIS ---
    req = SingleTaskClassificationRequest("Buy milk", ["Groceries"])
    response = classifier.classify_single(req)
    result = response.results[0]

    assert result.classification_type == "resource"
    assert result.suggested_project == "Groceries"

    # --- STEP 3: PROCESS (CONFIRM) ---
    draft = triage.create_draft("Buy milk", result)
    triage.apply_draft(draft)

    # Verify Inbox is empty
    assert "Buy milk" not in repo.data.inbox_tasks

    # Verify Item moved to Project
    project = repo.find_project_by_name("Groceries")
    assert len(project.items) == 1
    item = project.items[0]
    assert item.name == "Milk"
    assert item.kind == "resource"

    # --- STEP 4: EXECUTION ---
    # Verify it shows up in shopping list
    shopping_list = execution.get_shopping_list()
    assert "General" in shopping_list
    assert shopping_list["General"][0][0].name == "Milk"

    # --- STEP 5: COMPLETE ---
    execution.complete_item(item.id)
    assert item.is_acquired is True

    # --- STEP 6: PERSISTENCE ---
    repo.save()
    assert repo.is_dirty is False

    # Verify Disk Write
    saved_yaml = (repo.dm.base_path / "test_db" / "dataset.yaml").read_text()
    assert "is_acquired: true" in saved_yaml


def test_transition_incubate(e2e_env):
    """
    Transition: Non-Actionable -> Incubate
    Mechanism: 🤖 AI Suggested -> User Confirms
    Outcome: Task created with #someday tag.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]

    # 1. Capture
    text = "Learn guitar someday"
    triage.add_to_inbox(text)

    # 2. AI Analysis
    req = SingleTaskClassificationRequest(text, ["Groceries"])
    response = classifier.classify_single(req)
    result = response.results[0]

    assert result.classification_type == "incubate"

    # 3. User Confirms (Apply Draft)
    # Note: Since project is "Unmatched", user usually picks one.
    # For test, we force it into "Groceries" (ID 1)
    draft = triage.create_draft(text, result)
    triage.apply_draft(draft, override_project_id=1)

    # 4. Verify
    project = repo.find_project(1)
    item = project.items[0]
    assert isinstance(item, TaskItem)
    assert "someday" in item.tags
    assert item.notes == "Incubated from Triage"


def test_transition_reference(e2e_env):
    """
    Transition: Non-Actionable -> Reference
    Mechanism: 🤖 AI Suggested -> User Confirms
    Outcome: ReferenceItem created.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]

    text = "http://wiki.com"
    triage.add_to_inbox(text)

    # AI Analysis
    req = SingleTaskClassificationRequest(text, ["Groceries"])
    result = classifier.classify_single(req).results[0]

    assert result.classification_type == "reference"

    # User Confirms
    draft = triage.create_draft(text, result)
    triage.apply_draft(draft)  # AI suggested "Groceries", so no override needed

    # Verify
    project = repo.find_project(1)
    item = project.items[0]
    assert isinstance(item, ReferenceItem)
    assert item.content == text


def test_transition_new_project(e2e_env):
    """
    Transition: Actionable -> Multi-step -> New Project
    Mechanism: 🤖 AI Suggested -> User Confirms
    Outcome: New Project created, item moved inside.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]

    text = "Start a new project"
    triage.add_to_inbox(text)

    # AI Analysis
    req = SingleTaskClassificationRequest(text, ["Groceries"])
    result = classifier.classify_single(req).results[0]

    assert result.classification_type == "new_project"
    assert result.suggested_new_project_name == "New Big Goal"

    # User Confirms (Calls specific create method)
    draft = triage.create_draft(text, result)
    triage.create_project_from_draft(draft, result.suggested_new_project_name)

    # Verify
    assert len(repo.data.projects) == 2  # Groceries + New Big Goal
    new_proj = repo.data.projects[1]
    assert new_proj.name == "New Big Goal"
    assert len(new_proj.items) == 1
    assert new_proj.items[0].name == "Launch Rocket"


def test_transition_trash_manual(e2e_env):
    """
    Transition: Non-Actionable -> Trash
    Mechanism: 👤 Manual Only (User clicks Trash)
    Outcome: Item deleted, no entity created.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]

    text = "Total junk text"
    triage.add_to_inbox(text)

    # AI Analysis (AI tries to be helpful and suggests Task)
    req = SingleTaskClassificationRequest(text, ["Groceries"])
    result = classifier.classify_single(req).results[0]
    assert result.classification_type == "task"  # AI didn't say trash

    # User Decision: "No, this is trash" -> Click Trash Button
    triage.delete_inbox_item(text)

    # Verify
    assert text not in repo.data.inbox_tasks
    assert len(repo.data.projects[0].items) == 0  # Nothing added


def test_transition_override(e2e_env):
    """
    Transition: Actionable -> Project Check
    Mechanism: 🔄 Override (User disagrees with AI)
    Outcome: Item moved to user-selected project, not AI-selected one.
    """
    triage = e2e_env["triage"]
    classifier = e2e_env["classifier"]
    repo = e2e_env["repo"]

    text = "Buy milk"
    triage.add_to_inbox(text)

    # AI Analysis (Suggests "Groceries")
    req = SingleTaskClassificationRequest(text, ["Groceries"])
    result = classifier.classify_single(req).results[0]
    assert result.suggested_project == "Groceries"

    # User Decision: Override! Move to a new project "Errands" (simulated)
    # 1. User creates "Errands" manually or it exists
    repo.data.projects.append(Project(id=2, name="Errands"))

    # 2. User clicks "Move to Errands" (Manual Assignment)
    triage.move_inbox_item_to_project(text, 2, ["manual_tag"])

    # Verify
    groceries = repo.find_project(1)
    errands = repo.find_project(2)

    assert len(groceries.items) == 0  # AI suggestion ignored
    assert len(errands.items) == 1  # Manual choice respected
    assert errands.items[0].name == "Buy milk"