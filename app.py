import streamlit as st
import anthropic
from typing import List

# --- Import Infrastructure & Domain ---
from services import DatasetManager, PromptBuilder, TaskClassifier
from services.repository import YamlRepository, TriageService, PlanningService, ExecutionService
from models.dtos import SingleTaskClassificationRequest
from models.entities import ResourceType, ProjectStatus

# --- Import Views ---
# We assume pages/shopping_view.py exists as created in previous steps
try:
    from pages.shopping_view import render_shopping_view
except ImportError:
    # Fallback if file structure isn't perfect yet
    def render_shopping_view(service):
        st.error("Shopping view module not found. Please ensure pages/shopping_view.py exists.")

# --- Configuration ---
st.set_page_config(page_title="GTD Task Triage", layout="wide", initial_sidebar_state="expanded")

# --- CSS Styling ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
        h4 { font-size: 1.1rem !important; margin-bottom: 0.2rem !important; }
        .ai-hint { font-size: 0.9rem; color: #888; font-style: italic; margin-bottom: 1rem; }
        .dest-project { font-size: 1.3rem; font-weight: bold; color: #4DA6FF; margin-bottom: 0.5rem; }

        /* Card Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #1E1E1E;
            border-radius: 12px;
            padding: 1rem;
        }

        /* Button Hacks */
        button:has(p:contains("Add")) { background-color: #28a745 !important; border-color: #28a745 !important; }
        button:has(p:contains("Skip")) { background-color: #007bff !important; border-color: #007bff !important; }
    </style>
""", unsafe_allow_html=True)


# --- 1. Infrastructure Setup (Cached) ---
@st.cache_resource
def get_infrastructure():
    """Initialize stateless infrastructure components"""
    dataset_manager = DatasetManager()

    # AI Setup
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not found in secrets.")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    prompt_builder = PromptBuilder()
    classifier = TaskClassifier(client, prompt_builder)

    return dataset_manager, classifier


dataset_manager, classifier = get_infrastructure()

# --- 2. Session State & Repository Management ---

if 'dataset_name' not in st.session_state:
    st.session_state.dataset_name = None

# Sidebar: Load/Save
with st.sidebar:
    st.header("🗂️ System")

    # Dataset Loader
    available_datasets = dataset_manager.list_datasets()
    selected_dataset = st.selectbox(
        "Select Dataset",
        available_datasets,
        index=available_datasets.index(
            st.session_state.dataset_name) if st.session_state.dataset_name in available_datasets else 0
    )

    if st.button("📂 Load Dataset", use_container_width=True):
        st.session_state.dataset_name = selected_dataset
        # Clear AI cache on load
        if 'current_prediction' in st.session_state: del st.session_state.current_prediction
        st.rerun()

    st.divider()

# Stop if no dataset loaded
if not st.session_state.dataset_name:
    st.info("👈 Please load a dataset from the sidebar to begin.")
    st.stop()

# Initialize Repository & Services
# We re-initialize these on every run to ensure we have the latest state from memory/disk
# The YamlRepository handles the actual data holding
try:
    repo = YamlRepository(dataset_manager, st.session_state.dataset_name)
    triage_service = TriageService(repo)
    planning_service = PlanningService(repo)
    execution_service = ExecutionService(repo)
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

# --- 3. Navigation ---
mode = st.sidebar.radio(
    "Mode",
    ["📥 Triage", "🎯 Planning", "✅ Execution", "🛒 Shopping"]
)

# --- VIEW 1: TRIAGE (Capture & Clarify) ---
if mode == "📥 Triage":
    st.title("📥 Inbox Triage")

    # 1. Quick Capture
    with st.form("quick_capture", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        new_task = c1.text_input("Capture thought...", placeholder="e.g., Buy milk")
        if c2.form_submit_button("Capture"):
            if new_task:
                triage_service.add_to_inbox(new_task)
                st.rerun()

    # 2. Process Inbox
    inbox_items = triage_service.get_inbox_items()

    if not inbox_items:
        st.success("🎉 Inbox Zero! You are all caught up.")
        st.balloons()
    else:
        # Progress Bar
        total_tasks = len(inbox_items) + sum(len(p.tasks) for p in repo.data.projects)
        st.progress((total_tasks - len(inbox_items)) / total_tasks if total_tasks > 0 else 1.0)

        current_task_text = inbox_items[0]

        # AI Prediction Logic
        if 'current_prediction' not in st.session_state or st.session_state.get(
                'current_task_ref') != current_task_text:
            with st.spinner("🤖 AI is analyzing..."):
                # Get project names for AI context
                project_names = [p.name for p in repo.data.projects]

                req = SingleTaskClassificationRequest(
                    task_text=current_task_text,
                    available_projects=project_names
                )
                response = classifier.classify_single(req)
                st.session_state.current_prediction = response
                st.session_state.current_task_ref = current_task_text

        result = st.session_state.current_prediction.results[0]

        # The Card
        with st.container(border=True):
            st.markdown(f"#### {current_task_text}")

            if result.suggested_project != "Unmatched":
                st.markdown(f"<div class='ai-hint'>💡 {result.reasoning}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dest-project'>➡️ {result.suggested_project}</div>", unsafe_allow_html=True)

                # Tags display
                if result.extracted_tags:
                    st.caption(f"Tags: {', '.join(result.extracted_tags)}")

                # Action Buttons
                col_add, col_skip = st.columns([1, 4])

                # Find project ID for the suggestion
                target_proj = next((p for p in repo.data.projects if p.name == result.suggested_project), None)

                if col_add.button("Add", type="primary", use_container_width=True):
                    if target_proj:
                        triage_service.move_inbox_item_to_project(
                            current_task_text,
                            target_proj.id,
                            result.extracted_tags
                        )
                        st.rerun()
            else:
                st.warning("❓ AI couldn't find a good match.")

        # Manual Override
        st.markdown("---")
        st.caption("Manual Assignment")

        # Existing Projects
        project_options = {p.name: p.id for p in repo.data.projects}
        selected_proj_name = st.selectbox("Move to...", ["Select..."] + list(project_options.keys()),
                                          label_visibility="collapsed")

        if selected_proj_name != "Select...":
            triage_service.move_inbox_item_to_project(current_task_text, project_options[selected_proj_name], [])
            st.rerun()

        # Create New Project
        with st.expander("Or Create New Project"):
            new_proj_name = st.text_input("New Project Name")
            if st.button("Create & Move"):
                triage_service.create_project_from_inbox(current_task_text, new_proj_name)
                st.rerun()

        # Skip
        if st.button("⏭️ Skip for now", use_container_width=True):
            triage_service.skip_inbox_item(current_task_text)
            del st.session_state.current_prediction
            st.rerun()

# --- VIEW 2: PLANNING (Organize & Review) ---
elif mode == "🎯 Planning":
    st.title("🎯 Planning & Review")

    # 1. Create Goal
    with st.expander("➕ Create New Goal"):
        with st.form("new_goal"):
            g_name = st.text_input("Goal Name")
            g_desc = st.text_area("Description")
            if st.form_submit_button("Create Goal"):
                planning_service.create_goal(g_name, g_desc)
                st.success("Goal created!")
                st.rerun()

    # 2. Display Goals
    goals = planning_service.get_all_goals()
    orphaned_projects = planning_service.get_orphaned_projects()


    # Helper to render project details
    def render_project_details(project):
        st.markdown(f"**{project.name}**")

        tab_res, tab_ref = st.tabs(["📦 Resources (Shop/Prep)", "📚 Reference"])

        with tab_res:
            # Add Resource Form
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            res_name = c1.text_input("Item", key=f"rn_{project.id}", label_visibility="collapsed",
                                     placeholder="Item name")
            res_type = c2.selectbox("Type", [ResourceType.TO_BUY.value, ResourceType.TO_GATHER.value],
                                    key=f"rt_{project.id}", label_visibility="collapsed")
            res_store = c3.text_input("Store/Loc", key=f"rs_{project.id}", label_visibility="collapsed",
                                      placeholder="Store")

            if c4.button("➕", key=f"add_r_{project.id}"):
                r_enum = ResourceType(res_type)
                planning_service.add_resource(project.id, res_name, r_enum, res_store)
                st.rerun()

            # List Resources
            if project.resources:
                for r in project.resources:
                    icon = "🛒" if r.type == ResourceType.TO_BUY else "🧤"
                    st.text(f"{icon} {r.name} ({r.store})")
            else:
                st.caption("No resources needed yet.")

        with tab_ref:
            # Add Reference Form
            c1, c2 = st.columns([5, 1])
            ref_name = c1.text_input("Ref Note", key=f"refn_{project.id}", label_visibility="collapsed")
            if c2.button("➕", key=f"add_ref_{project.id}"):
                planning_service.add_reference_item(project.id, ref_name, "")
                st.rerun()

            for ref in project.reference_items:
                st.text(f"📄 {ref.name}")


    # Render Goals
    for goal in goals:
        with st.expander(f"🏆 {goal.name}", expanded=True):
            st.caption(goal.description)
            projects = planning_service.get_projects_for_goal(goal.id)

            if not projects:
                st.info("No projects linked to this goal.")

            for proj in projects:
                with st.container(border=True):
                    render_project_details(proj)

    # Render Orphans
    if orphaned_projects:
        with st.expander("📂 Projects without Goals", expanded=False):
            for proj in orphaned_projects:
                with st.container(border=True):
                    render_project_details(proj)

# --- VIEW 3: EXECUTION (Engage) ---
elif mode == "✅ Execution":
    st.title("✅ Next Actions")

    # Context Filter
    all_tags = set()
    for p in repo.data.projects:
        for t in p.tasks:
            all_tags.update(t.tags)

    selected_tag = st.pills("Context", list(all_tags), selection_mode="single")

    # Get Tasks
    tasks = execution_service.get_next_actions(context_filter=selected_tag)

    if not tasks:
        st.info("No active tasks found for this context.")

    # Group by Project for context
    # (Alternatively, could be a flat list, but grouping helps context)
    for task in tasks:
        # Find parent project name (inefficient lookup but fine for prototype)
        parent_proj = next((p for p in repo.data.projects if task in p.tasks), None)
        proj_name = parent_proj.name if parent_proj else "Unknown"

        col1, col2 = st.columns([0.5, 10])

        # Completion Checkbox
        is_done = col1.checkbox("Done", value=False, key=f"exec_{task.id}", label_visibility="collapsed")

        if is_done:
            execution_service.complete_task(parent_proj.id, task.id)
            st.toast(f"Completed: {task.name}")
            st.rerun()