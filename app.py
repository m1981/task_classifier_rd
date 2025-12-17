import streamlit as st
import anthropic
import time

# --- Import Infrastructure & Domain ---
from services import DatasetManager, PromptBuilder, TaskClassifier
from services.repository import TriageService, PlanningService, ExecutionService
from services.snapshot_service import SnapshotService

# --- Import Views ---
from views.common import inject_custom_css, log_action
from views.triage_view import render_triage_view
from views.planning_view import render_planning_view
from views.execution_view import render_execution_view
from views.shopping_view import render_shopping_view

# --- Configuration ---
st.set_page_config(page_title="GTD Task Triage", layout="wide", initial_sidebar_state="expanded")
inject_custom_css()


# ==========================================
# 1. INFRASTRUCTURE & STATE INITIALIZATION
# ==========================================

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

# Initialize Session State Keys if missing
if 'dataset_name' not in st.session_state:
    st.session_state.dataset_name = None


# ==========================================
# 2. CONTROLLER LOGIC (Pre-Render)
# ==========================================

def ensure_repository_loaded():
    """
    Ensures the repository is loaded into session state matching the selected dataset.
    Runs BEFORE any UI rendering to prevent glitches.
    """
    if st.session_state.dataset_name:
        # Check if we need to load (Repo missing OR Repo name mismatch)
        should_load = False
        if 'repo' not in st.session_state:
            should_load = True
        elif st.session_state.repo.name != st.session_state.dataset_name:
            should_load = True

        if should_load:
            try:
                log_action("DB CONNECT", f"Connecting to {st.session_state.dataset_name}...")
                db_path = dataset_manager.load_dataset(st.session_state.dataset_name)

                from services.repository import SqliteRepository
                new_repo = SqliteRepository(db_path)

                # CRITICAL FIX: Update the repo name to match the dataset name
                # This prevents the infinite loop on the next run
                new_repo.name = st.session_state.dataset_name

                st.session_state.repo = new_repo

                # NOTE: We do NOT need st.rerun() here because this runs before the UI.
                # The rest of the script will see the new repo immediately.
            except Exception as e:
                st.error(f"Failed to load dataset: {e}")
                st.stop()


# Run the loader logic
ensure_repository_loaded()

# Initialize Services (if repo exists)
triage_service = None
planning_service = None
execution_service = None

if 'repo' in st.session_state:
    repo = st.session_state.repo
    triage_service = TriageService(repo)
    planning_service = PlanningService(repo)
    execution_service = ExecutionService(repo)

# ==========================================
# 3. VIEW RENDERING (Sidebar)
# ==========================================

with st.sidebar:
    st.header("🗂️ System")

    # Dataset Selector
    available_datasets = dataset_manager.list_datasets()
    index = 0
    if st.session_state.dataset_name in available_datasets:
        index = available_datasets.index(st.session_state.dataset_name)

    selected_dataset = st.selectbox(
        "Select Dataset",
        available_datasets,
        index=index,
        key="dataset_selector"
    )

    # Load Button
    if st.button("📂 Load Dataset", use_container_width=True):
        st.session_state.dataset_name = selected_dataset
        # Clear AI cache
        if 'current_prediction' in st.session_state: del st.session_state.current_prediction
        # Clear Repo to force reload in Controller
        if 'repo' in st.session_state: del st.session_state.repo
        st.rerun()

    st.divider()

    # Scenario Manager
    if 'repo' in st.session_state:
        st.subheader("🧪 Scenarios")
        snapshot_svc = SnapshotService(st.session_state.repo)

        # Export
        try:
            json_data = snapshot_svc.export_to_json()
            st.download_button(
                label="📸 Export Snapshot",
                data=json_data,
                file_name=f"{st.session_state.dataset_name}_snapshot.json",
                mime="application/json",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Export Error: {e}")

        # Import
        uploaded_file = st.file_uploader("Restore Scenario", type=["json"], label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("⚠️ Overwrite DB & Restore", type="secondary", use_container_width=True):
                try:
                    json_str = uploaded_file.getvalue().decode("utf-8")
                    snapshot_svc.restore_from_json(json_str)
                    st.success("Restored!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Restore failed: {e}")
        st.divider()

    # Navigation
    mode = st.sidebar.radio(
        "Mode",
        ["📥 Triage", "🎯 Planning", "✅ Execution", "🛒 Shopping"]
    )

    st.divider()

    if st.button("💾 Force Save", type="primary", use_container_width=True):
        if 'repo' in st.session_state:
            st.session_state.repo.save()
            st.toast("Saved!", icon="💾")

# ==========================================
# 4. VIEW RENDERING (Main Content)
# ==========================================

if not st.session_state.dataset_name:
    st.info("👈 Please load a dataset from the sidebar to begin.")
    st.stop()

if 'repo' in st.session_state and triage_service:
    if mode == "📥 Triage":
        render_triage_view(triage_service, classifier, st.session_state.repo)
    elif mode == "🎯 Planning":
        render_planning_view(planning_service)
    elif mode == "✅ Execution":
        render_execution_view(execution_service, st.session_state.repo)
    elif mode == "🛒 Shopping":
        render_shopping_view(execution_service)