import streamlit as st
import anthropic
import json
from services import DatasetManager, SaveDatasetCommand, DatasetProjector
from models import Project, Task

# --- Configuration ---
st.set_page_config(page_title="Task Triage", layout="wide", initial_sidebar_state="collapsed")

# --- CSS: Visual Styling ---
st.markdown("""
    <style>
        /* Clean up spacing */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }

        /* Typography */
        h4 { font-size: 1.1rem !important; margin-bottom: 0.2rem !important; }
        .ai-hint { font-size: 0.9rem; color: #888; font-style: italic; margin-bottom: 1rem; }
        .dest-project { font-size: 1.3rem; font-weight: bold; color: #4DA6FF; margin-bottom: 0.5rem; }

        /* Card Background */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #1E1E1E;
            border-radius: 12px;
            padding: 1rem;
        }

        /* Hide Footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* --- BUTTON COLOR HACKS --- */

        /* 1. Target the Main "Add" button (Green) */
        /* We look for the button containing the text "Add" inside the main card area */
        div[data-testid="stVerticalBlockBorderWrapper"] button p:contains("Add") {
            color: white !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] button:has(p:contains("Add")) {
            background-color: #28a745 !important;
            border-color: #28a745 !important;
        }

        /* 2. Target the "Skip" button (Blue) */
        button:has(p:contains("Skip")) {
            background-color: #007bff !important;
            border-color: #007bff !important;
        }
    </style>

    <!-- JS Fallback for older browsers that don't support :has() CSS -->
    <script>
        const buttons = window.parent.document.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText === "Add") {
                btn.style.backgroundColor = "#28a745";
                btn.style.borderColor = "#28a745";
                btn.style.color = "white";
            }
            if (btn.innerText.includes("Skip")) {
                btn.style.backgroundColor = "#007bff";
                btn.style.borderColor = "#007bff";
                btn.style.color = "white";
            }
        });
    </script>
""", unsafe_allow_html=True)


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


# --- Helper Functions ---
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
        "reasoning": "Max 10 words explanation",
        "tags": ["tag1"]
    }}
    """
    result_structure = {"parsed": None, "debug_prompt": prompt, "debug_raw_response": ""}
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text
        result_structure["debug_raw_response"] = content
        clean_json = content.replace("```json", "").replace("```", "").strip()
        result_structure["parsed"] = json.loads(clean_json)
    except Exception as e:
        result_structure["parsed"] = {
            "suggested_project": "Unmatched",
            "confidence": 0.0,
            "reasoning": "Error",
            "tags": []
        }
        result_structure["debug_raw_response"] = str(e)
    return result_structure


def move_task_to_project(dataset, task_text, project_name, tags=None):
    target_project = next((p for p in dataset.projects if p.name == project_name), None)
    if not target_project: return

    new_task_id = len(target_project.tasks) + 1
    new_task = Task(id=new_task_id, name=task_text, tags=tags if tags else [], duration="unknown")
    target_project.tasks.append(new_task)

    if task_text in dataset.inbox_tasks:
        dataset.inbox_tasks.remove(task_text)

    if 'current_prediction' in st.session_state: del st.session_state.current_prediction
    if 'history' not in st.session_state: st.session_state.history = []
    st.session_state.history.insert(0, f"Moved '{task_text}' → {project_name}")


def create_project_and_move(dataset, task_text, new_project_name):
    if any(p.name.lower() == new_project_name.lower() for p in dataset.projects):
        move_task_to_project(dataset, task_text, new_project_name)
        return
    new_id = max([p.id for p in dataset.projects], default=0) + 1
    new_proj = Project(id=new_id, name=new_project_name)
    dataset.projects.append(new_proj)
    move_task_to_project(dataset, task_text, new_project_name)


# --- UI LAYOUT ---

# 1. SIDEBAR
with st.sidebar:
    st.header("⚙️ Settings")
    available_datasets = services['dataset_manager'].list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("Dataset", available_datasets)
        if st.button("📂 Load", use_container_width=True):
            try:
                dataset = services['dataset_manager'].load_dataset(selected_dataset)
                st.session_state.dataset = dataset
                if 'current_prediction' in st.session_state: del st.session_state.current_prediction
                if 'history' in st.session_state: del st.session_state.history
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    if 'dataset' in st.session_state:
        new_name = st.text_input("Filename", value=selected_dataset)
        if st.button("💾 Save", type="primary", use_container_width=True):
            req = services['projector'].from_ui_state(st.session_state.dataset, new_name)
            services['save_command'].execute(req, st.session_state.dataset)
            st.toast("Saved!", icon="💾")

# 2. MAIN SCREEN
if 'dataset' not in st.session_state:
    st.info("👈 Load dataset in sidebar.")
    st.stop()

dataset = st.session_state.dataset

# Header
if dataset.inbox_tasks:
    total = len(dataset.inbox_tasks) + sum(len(p.tasks) for p in dataset.projects)
    done = sum(len(p.tasks) for p in dataset.projects)
    c1, c2 = st.columns([1, 4])
    c1.markdown(f"**Inbox: {len(dataset.inbox_tasks)}**")
    c2.progress(done / total if total > 0 else 0)
else:
    st.progress(1.0)

# Main Logic
if not dataset.inbox_tasks:
    st.success("🎉 Inbox Zero!")
else:
    current_task_text = dataset.inbox_tasks[0]

    # AI Prediction
    if 'current_prediction' not in st.session_state or st.session_state.current_task_ref != current_task_text:
        with st.spinner("..."):
            full_result = analyze_single_task(services['client'], current_task_text, [p.name for p in dataset.projects])
            st.session_state.current_prediction = full_result
            st.session_state.current_task_ref = current_task_text

    full_result = st.session_state.current_prediction
    parsed_pred = full_result['parsed']

    # --- THE CARD ---
    with st.container(border=True):
        # 1. Task Name
        st.markdown(f"#### {current_task_text}")

        # 2. AI Hint
        if parsed_pred['suggested_project'] != "Unmatched":
            st.markdown(f"<div class='ai-hint'>💡 {parsed_pred['reasoning']}</div>", unsafe_allow_html=True)

            # 3. Project Name (Destination)
            st.markdown(f"<div class='dest-project'>➡️ {parsed_pred['suggested_project']}</div>",
                        unsafe_allow_html=True)

            # 4. Add Button (Narrow, Green via CSS)
            # We use columns to make the button narrow (not full width)
            b_col1, b_col2 = st.columns([1, 3])
            if b_col1.button("Add", type="primary"):
                move_task_to_project(dataset, current_task_text, parsed_pred['suggested_project'],
                                     parsed_pred.get('tags'))
                st.rerun()
        else:
            st.warning("❓ Unsure where to put this.")

    # --- MANUAL SELECTION ---
    project_options = [p.name for p in dataset.projects if p.name != parsed_pred['suggested_project']]
    selected_project = st.pills("Manual", project_options, selection_mode="single", label_visibility="collapsed")

    if selected_project:
        move_task_to_project(dataset, current_task_text, selected_project)
        st.rerun()

    st.markdown("---")

    # --- CREATE NEW ---
    with st.form(key="create_form", clear_on_submit=True, border=False):
        c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")
        new_proj_name = c_input.text_input("New Project", placeholder="New Project Name", label_visibility="collapsed")
        if c_btn.form_submit_button("Create"):
            if new_proj_name:
                create_project_and_move(dataset, current_task_text, new_proj_name)
                st.rerun()

    # --- SKIP ---
    if st.button("⏭️ Skip", use_container_width=True):
        task = dataset.inbox_tasks.pop(0)
        dataset.inbox_tasks.append(task)
        del st.session_state.current_prediction
        st.rerun()

    # --- DEBUG SECTION ---
    st.markdown("---")
    with st.expander("🛠️ Debug Info"):
        st.markdown("**Prompt:**")
        st.text(full_result.get('debug_prompt', ''))
        st.markdown("**Response:**")
        st.code(full_result.get('debug_raw_response', ''), language='json')