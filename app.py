import streamlit as st
import anthropic
from typing import List
import functools
import time
import sys


# --- DEBUG LOGGING UTILITY ---
def debug_log(func):
    """Decorator to print function calls, args, and execution time to stdout."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Format arguments for display
        arg_str = ", ".join([repr(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v!r}" for k, v in kwargs.items()])
        all_args = ", ".join(filter(None, [arg_str, kwarg_str]))

        # Truncate long strings for readability
        if len(all_args) > 100:
            all_args = all_args[:97] + "..."

        print(f"➡️  CALL: {func.__name__}({all_args})")
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000

            # Format result
            res_str = repr(result)
            if len(res_str) > 100:
                res_str = res_str[:97] + "..."

            print(f"✅  RETURN: {func.__name__} in {elapsed:.2f}ms -> {res_str}")
            return result
        except Exception as e:
            print(f"❌  ERROR in {func.__name__}: {str(e)}")
            raise e

    return wrapper

# --- Import Infrastructure & Domain ---
from services import DatasetManager, PromptBuilder, TaskClassifier
from services.repository import YamlRepository, TriageService, PlanningService, ExecutionService
from models.dtos import SingleTaskClassificationRequest
from models.entities import ResourceType, ProjectStatus

# --- DEBUG LOGGER ---
def log_action(action: str, details: str):
    print(f"\n[ACTION] {action}")
    print(f"   └── {details}")

def log_state(label: str, data):
    print(f"[STATE] {label}: {data}")

# --- Import Views ---
try:
    from pages.shopping_view import render_shopping_view
except ImportError:
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
    # Handle case where no datasets exist
    index = 0
    if st.session_state.dataset_name in available_datasets:
        index = available_datasets.index(st.session_state.dataset_name)

    selected_dataset = st.selectbox("Select Dataset", available_datasets, index=index)

    if st.button("📂 Load Dataset", use_container_width=True):
        log_action("LOAD DATASET", selected_dataset)
        st.session_state.dataset_name = selected_dataset
        # Clear AI cache on load
        if 'current_prediction' in st.session_state: del st.session_state.current_prediction
        # Force reload of repo on explicit load button click
        if 'repo' in st.session_state: del st.session_state.repo
        st.rerun()

    st.divider()

# Stop if no dataset loaded
if not st.session_state.dataset_name:
    st.info("👈 Please load a dataset from the sidebar to begin.")
    st.stop()

# Initialize Repository & Services
try:
    # Check if we need to load the repo from disk (First run OR dataset changed)
    if 'repo' not in st.session_state or st.session_state.repo.name != st.session_state.dataset_name:
        log_action("DISK I/O", f"Loading {st.session_state.dataset_name} from file...")
        st.session_state.repo = YamlRepository(dataset_manager, st.session_state.dataset_name)

    # Use the persistent repository object
    repo = st.session_state.repo

    # Services are stateless wrappers, so we can re-init them passing the persistent repo
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
                log_action("CAPTURE", new_task)
                triage_service.add_to_inbox(new_task)
                st.rerun()

    # 2. Process Inbox
    inbox_items = triage_service.get_inbox_items()

    # DEBUG LOG: Print current inbox state
    log_state("Current Inbox", inbox_items)

    if not inbox_items:
        st.success("🎉 Inbox Zero! You are all caught up.")
        st.balloons()
    else:
        # Progress Bar
        total_tasks = len(inbox_items) + sum(len(p.tasks) for p in repo.data.projects)
        st.progress((total_tasks - len(inbox_items)) / total_tasks if total_tasks > 0 else 1.0)

        current_task_text = inbox_items[0]

        # AI Prediction
        if 'current_prediction' not in st.session_state or st.session_state.get('current_task_ref') != current_task_text:
            log_action("AI PREDICTION START", current_task_text)
            with st.spinner("🤖 AI is analyzing..."):
                project_names = [p.name for p in repo.data.projects]

                req = SingleTaskClassificationRequest(
                    task_text=current_task_text,
                    available_projects=project_names
                )
                response = classifier.classify_single(req)
                st.session_state.current_prediction = response
                st.session_state.current_task_ref = current_task_text
                log_action("AI PREDICTION DONE", f"Suggested: {response.results[0].suggested_project}")

        # Get Result
        response_obj = st.session_state.current_prediction
        result = response_obj.results[0]

        # --- THE CARD ---
        with st.container(border=True):
            st.markdown(f"#### {current_task_text}")

            if result.suggested_project != "Unmatched":
                st.markdown(f"<div class='ai-hint'>💡 {result.reasoning}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dest-project'>➡️ {result.suggested_project}</div>", unsafe_allow_html=True)
                if result.extracted_tags: st.caption(f"Tags: {', '.join(result.extracted_tags)}")

                if result.extracted_tags:
                    st.caption(f"Tags: {', '.join(result.extracted_tags)}")

                # Action Buttons
                col_add, col_skip = st.columns([1, 4])

                target_proj = next((p for p in repo.data.projects if p.name == result.suggested_project), None)

                if col_add.button("Add", type="primary", use_container_width=True):
                    if target_proj:
                        log_action("ADD TASK", f"{current_task_text} -> {target_proj.name}")
                        triage_service.move_inbox_item_to_project(current_task_text, target_proj.id, result.extracted_tags)
                        st.rerun()
            else:
                st.warning("❓ Unsure where to put this.")
                st.caption(f"Reasoning: {result.reasoning}")

        # --- MANUAL SELECTION (PILLS) ---
        # Filter out the suggested project from options to avoid redundancy
        project_options = [p.name for p in repo.data.projects if p.name != result.suggested_project]

        # Use Pills for manual selection
        selected_project = st.pills("Manual Assignment", project_options, selection_mode="single")

        if selected_project:
            log_action("MANUAL MOVE", f"{current_task_text} -> {selected_project}")
            target_id = next(p.id for p in repo.data.projects if p.name == selected_project)
            triage_service.move_inbox_item_to_project(current_task_text, target_id, [])
            st.rerun()

        st.markdown("---")

        # --- CREATE NEW PROJECT ---
        # Logic: Expand if Unmatched, or if AI suggested a new name
        should_expand = (result.suggested_project == "Unmatched")

        # Logic: Pre-fill with AI suggestion if available
        default_new_name = ""
        if hasattr(result, 'suggested_new_project_name') and result.suggested_new_project_name:
            default_new_name = result.suggested_new_project_name

        with st.expander("➕ Create New Project", expanded=should_expand):
            with st.form(key="create_form", clear_on_submit=True, border=False):
                c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")
                new_proj_name = c_input.text_input(
                    "New Project Name",
                    value=default_new_name,
                    placeholder="e.g., Bedroom Paint"
                )
                if c_btn.form_submit_button("Create & Move"):
                    if new_proj_name:
                        log_action("CREATE PROJECT", new_proj_name)
                        triage_service.create_project_from_inbox(current_task_text, new_proj_name)
                        st.rerun()

        # --- SKIP ---
        if st.button("⏭️ Skip for now", use_container_width=True):
            log_action("SKIP CLICKED", current_task_text)

            # 1. Call Service
            triage_service.skip_inbox_item(current_task_text)

            # 2. Verify Change in Memory
            log_state("Inbox After Skip (Memory)", repo.data.inbox_tasks)

            # 3. Clear Session State
            if 'current_prediction' in st.session_state:
                del st.session_state.current_prediction
            if 'current_task_ref' in st.session_state:
                del st.session_state.current_task_ref

            st.rerun()

        # --- DEBUG SECTION ---
        st.markdown("---")
        with st.expander("🛠️ Debug Info"):
            st.text(f"Prompt: {response_obj.prompt_used}")
            st.code(response_obj.raw_response, language='json')

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


    def render_project_details(project):
        st.markdown(f"**{project.name}**")

        tab_res, tab_ref = st.tabs(["📦 Resources", "📚 Reference"])

        with tab_res:
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

            if project.resources:
                for r in project.resources:
                    icon = "🛒" if r.type == ResourceType.TO_BUY else "🧤"
                    st.text(f"{icon} {r.name} ({r.store})")
            else:
                st.caption("No resources needed yet.")

        with tab_ref:
            c1, c2 = st.columns([5, 1])
            ref_name = c1.text_input("Ref Note", key=f"refn_{project.id}", label_visibility="collapsed")
            if c2.button("➕", key=f"add_ref_{project.id}"):
                planning_service.add_reference_item(project.id, ref_name, "")
                st.rerun()
            for ref in project.reference_items:
                st.text(f"📄 {ref.name}")


    for goal in goals:
        with st.expander(f"🏆 {goal.name}", expanded=True):
            st.caption(goal.description)
            projects = planning_service.get_projects_for_goal(goal.id)
            if not projects:
                st.info("No projects linked to this goal.")
            for proj in projects:
                with st.container(border=True):
                    render_project_details(proj)

    if orphaned_projects:
        with st.expander("📂 Projects without Goals", expanded=False):
            for proj in orphaned_projects:
                with st.container(border=True):
                    render_project_details(proj)

# --- VIEW 3: EXECUTION (Engage) ---
elif mode == "✅ Execution":
    st.title("✅ Next Actions")

    all_tags = set()
    for p in repo.data.projects:
        for t in p.tasks:
            all_tags.update(t.tags)

    selected_tag = st.pills("Context", list(all_tags), selection_mode="single")

    tasks = execution_service.get_next_actions(context_filter=selected_tag)

    if not tasks:
        st.info("No active tasks found for this context.")

    for task in tasks:
        parent_proj = next((p for p in repo.data.projects if task in p.tasks), None)
        proj_name = parent_proj.name if parent_proj else "Unknown"

        col1, col2 = st.columns([0.5, 10])
        is_done = col1.checkbox("Done", value=False, key=f"exec_{task.id}", label_visibility="collapsed")

        if is_done:
            execution_service.complete_task(parent_proj.id, task.id)
            st.toast(f"Completed: {task.name}")
            st.rerun()

        col2.markdown(f"**{task.name}** <span style='color:gray; font-size:0.8em'>({proj_name})</span>",
                      unsafe_allow_html=True)
        if task.tags:
            col2.caption(f"🏷️ {', '.join(task.tags)}")

# --- VIEW 4: SHOPPING (Cross-Cutting) ---
elif mode == "🛒 Shopping":
    render_shopping_view(execution_service)

# --- GLOBAL FOOTER ---
st.sidebar.divider()
if st.sidebar.button("💾 Save All Changes", type="primary"):
    log_action("SAVE", "Writing to disk...")
    repo.save()
    st.toast("Dataset saved successfully!", icon="💾")