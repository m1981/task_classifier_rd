import streamlit as st
import anthropic
import json
from services import DatasetManager, SaveDatasetCommand, DatasetProjector
from models import Project, Task

# --- Configuration ---
# We keep layout="wide" so it stretches nicely on desktop,
# but the design is optimized for narrow screens.
st.set_page_config(page_title="AI Task Triage", layout="wide", initial_sidebar_state="collapsed")


# --- Service Initialization ---
@st.cache_resource
def get_services():
    dataset_manager = DatasetManager()
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    projector = DatasetProjector()
    save_command = SaveDatasetCommand(dataset_manager, projector)

    return {
        'dataset_manager': dataset_manager,
        'client': client,
        'projector': projector,
        'save_command': save_command
    }


services = get_services()


# --- Helper Functions (Logic Unchanged) ---

def analyze_single_task(client, task_text: str, projects: list[str]):
    project_list = ", ".join([f'"{p}"' for p in projects])
    prompt = f"""
    You are an expert task organizer.
    Task to classify: "{task_text}"
    Available Projects: [{project_list}]
    Analyze the task and return a JSON object (no markdown, just raw JSON) with these keys:
    {{
        "suggested_project": "The exact name of the best matching project from the list, or 'Unmatched'",
        "confidence": 0.95,
        "reasoning": "A short, punchy explanation why (max 15 words)",
        "tags": ["tag1", "tag2"]
    }}
    """
    result_structure = {"parsed": None}
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text
        clean_json = content.replace("```json", "").replace("```", "").strip()
        result_structure["parsed"] = json.loads(clean_json)
    except Exception as e:
        result_structure["parsed"] = {
            "suggested_project": "Unmatched",
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}",
            "tags": []
        }
    return result_structure


def move_task_to_project(dataset, task_text, project_name, tags=None):
    target_project = next((p for p in dataset.projects if p.name == project_name), None)
    if not target_project:
        st.error(f"Project '{project_name}' not found!")
        return

    new_task_id = len(target_project.tasks) + 1
    new_task = Task(id=new_task_id, name=task_text, tags=tags if tags else [], duration="unknown")
    target_project.tasks.append(new_task)

    if task_text in dataset.inbox_tasks:
        dataset.inbox_tasks.remove(task_text)

    if 'current_prediction' in st.session_state:
        del st.session_state.current_prediction

    if 'history' not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, f"Moved '{task_text}' → {project_name}")


def create_project_and_move(dataset, task_text, new_project_name):
    if any(p.name.lower() == new_project_name.lower() for p in dataset.projects):
        st.toast(f"Project '{new_project_name}' already exists, moving there.", icon="ℹ️")
        move_task_to_project(dataset, task_text, new_project_name)
        return

    new_id = max([p.id for p in dataset.projects], default=0) + 1
    new_proj = Project(id=new_id, name=new_project_name)
    dataset.projects.append(new_proj)
    move_task_to_project(dataset, task_text, new_project_name)


# --- UI LAYOUT START ---

# 1. SIDEBAR: Admin Controls (Hidden by default on mobile)
with st.sidebar:
    st.header("⚙️ Settings")

    # Dataset Loading
    available_datasets = services['dataset_manager'].list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("Dataset", available_datasets)
        if st.button("📂 Load", use_container_width=True):
            try:
                dataset = services['dataset_manager'].load_dataset(selected_dataset)
                st.session_state.dataset = dataset
                if 'current_prediction' in st.session_state: del st.session_state.current_prediction
                if 'history' in st.session_state: del st.session_state.history
                st.toast(f"Loaded {len(dataset.inbox_tasks)} tasks", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # Saving
    if 'dataset' in st.session_state:
        st.subheader("💾 Save")
        new_name = st.text_input("Filename", value=selected_dataset)
        if st.button("Save Progress", type="primary", use_container_width=True):
            req = services['projector'].from_ui_state(st.session_state.dataset, new_name)
            res = services['save_command'].execute(req, st.session_state.dataset)
            if res.success:
                st.toast("Progress Saved!", icon="💾")
            else:
                st.error(res.message)

        # History
        if 'history' in st.session_state and st.session_state.history:
            st.divider()
            st.caption("Recent History")
            for action in st.session_state.history[:5]:
                st.caption(f"• {action}")

# 2. MAIN SCREEN
if 'dataset' not in st.session_state:
    st.info("👈 Open the sidebar (top-left) to load a dataset.")
    st.stop()

dataset = st.session_state.dataset

# 2a. Compact Header (Progress Bar)
if dataset.inbox_tasks:
    total_tasks = len(dataset.inbox_tasks) + sum(len(p.tasks) for p in dataset.projects)
    processed = sum(len(p.tasks) for p in dataset.projects)
    progress = processed / total_tasks if total_tasks > 0 else 0

    # Use columns to put text and bar on same line
    h_col1, h_col2 = st.columns([1, 3])
    h_col1.caption(f"**Inbox: {len(dataset.inbox_tasks)}**")
    h_col2.progress(progress)
else:
    st.progress(1.0)

# 2b. Main Logic
if not dataset.inbox_tasks:
    st.balloons()
    st.success("🎉 Inbox Zero!")
    st.caption("Use the sidebar to save your work.")
else:
    current_task_text = dataset.inbox_tasks[0]

    # AI Prediction (Cached)
    if 'current_prediction' not in st.session_state or st.session_state.current_task_ref != current_task_text:
        with st.spinner("Thinking..."):
            full_result = analyze_single_task(
                services['client'],
                current_task_text,
                [p.name for p in dataset.projects]
            )
            st.session_state.current_prediction = full_result
            st.session_state.current_task_ref = current_task_text

    parsed_pred = st.session_state.current_prediction['parsed']

    # --- THE CARD (Mobile Optimized) ---
    with st.container(border=True):
        st.caption("Current Task")
        st.markdown(f"### {current_task_text}")

        # AI Suggestion Box
        if parsed_pred['suggested_project'] != "Unmatched":
            st.info(
                f"**💡 {parsed_pred['suggested_project']}**\n\n"
                f"_{parsed_pred['reasoning']}_"
            )
        else:
            st.warning(f"❓ Unsure. _{parsed_pred['reasoning']}_")

        st.write("")  # Spacer

        # PRIMARY ACTION: Big Button
        if parsed_pred['suggested_project'] != "Unmatched":
            if st.button(f"Move to {parsed_pred['suggested_project']}", type="primary", use_container_width=True):
                move_task_to_project(
                    dataset,
                    current_task_text,
                    parsed_pred['suggested_project'],
                    parsed_pred.get('tags')
                )
                st.rerun()

    # --- MANUAL OVERRIDES (Outside the card to reduce visual noise inside) ---
    st.write("")
    st.caption("Or choose manually:")

    # 1. Pills for existing projects (Horizontal scrolling/wrapping)
    # Filter out the suggested one to avoid duplicate options
    project_options = [p.name for p in dataset.projects if p.name != parsed_pred['suggested_project']]

    # st.pills is available in Streamlit 1.40+. If using older version, fallback to multiselect or buttons.
    selected_project = st.pills("Projects", project_options, selection_mode="single", label_visibility="collapsed")

    if selected_project:
        move_task_to_project(dataset, current_task_text, selected_project)
        st.rerun()

    # 2. Create New (Collapsed)
    with st.expander("➕ Create New Project"):
        c1, c2 = st.columns([3, 1])
        new_proj_name = c1.text_input("Name", placeholder="e.g. Vacation", label_visibility="collapsed")
        if c2.button("Add", use_container_width=True):
            if new_proj_name:
                create_project_and_move(dataset, current_task_text, new_proj_name)
                st.rerun()

    # 3. Skip (Bottom, low prominence)
    st.write("")
    if st.button("⏭️ Skip for now", use_container_width=True):
        task = dataset.inbox_tasks.pop(0)
        dataset.inbox_tasks.append(task)
        del st.session_state.current_prediction
        st.rerun()