import streamlit as st
import anthropic

# --- Import Infrastructure & Domain ---
from services import DatasetManager, PromptBuilder, TaskClassifier
from services.repository import TriageService, PlanningService, ExecutionService

# --- Import Views ---
from views.common import inject_custom_css, log_action
from views.triage_view import render_triage_view
from views.planning_view import render_planning_view
from views.execution_view import render_execution_view
from views.shopping_view import render_shopping_view

# --- Configuration ---
st.set_page_config(page_title="GTD Task Triage", layout="wide", initial_sidebar_state="expanded")
inject_custom_css()

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
    # Check if we need to load the repo
    if 'repo' not in st.session_state or st.session_state.repo.name != st.session_state.dataset_name:
        log_action("DB CONNECT", f"Connecting to {st.session_state.dataset_name}...")

        # Get path from manager
        db_path = dataset_manager.load_dataset(st.session_state.dataset_name)

        # Initialize SQL Repository
        from services.repository import SqliteRepository

        st.session_state.repo = SqliteRepository(db_path)

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

# --- 4. Routing ---
if mode == "📥 Triage":
    render_triage_view(triage_service, classifier, repo)

elif mode == "🎯 Planning":
    render_planning_view(planning_service)

elif mode == "✅ Execution":
    render_execution_view(execution_service, repo)

elif mode == "🛒 Shopping":
    render_shopping_view(execution_service)

# --- GLOBAL FOOTER ---
st.sidebar.divider()
if st.sidebar.button("💾 Save All Changes", type="primary"):
    log_action("SAVE", "Writing to disk...")
    repo.save()
    st.toast("Dataset saved successfully!", icon="💾")