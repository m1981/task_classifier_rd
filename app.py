import streamlit as st
import anthropic
import json
from services import DatasetManager, PromptBuilder, ResponseParser, TaskClassifier, SaveDatasetCommand, DatasetProjector
from models import Project, Task

# --- Configuration ---
st.set_page_config(page_title="AI Task Classification", layout="wide")


# --- Service Initialization ---
@st.cache_resource
def get_services():
    dataset_manager = DatasetManager()
    prompt_builder = PromptBuilder()
    response_parser = ResponseParser()

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    classifier = TaskClassifier(client, prompt_builder, response_parser)

    projector = DatasetProjector()
    save_command = SaveDatasetCommand(dataset_manager, projector)

    return {
        'dataset_manager': dataset_manager,
        'classifier': classifier,
        'client': client,  # Exposing client directly for single-task calls
        'projector': projector,
        'save_command': save_command
    }


services = get_services()


# --- Helper Functions for Single Task Workflow ---

def analyze_single_task(client, task_text: str, projects: list[str]):
    """
    Specialized function for the One-by-One workflow.
    We bypass the batch PromptBuilder to get specific JSON for a single item.
    """
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

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text
        # Clean potential markdown wrappers
        clean_json = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return {
            "suggested_project": "Unmatched",
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}",
            "tags": []
        }


def move_task_to_project(dataset, task_text, project_name, tags=None):
    """Moves a task string from inbox to a Project object"""
    # 1. Find the project
    target_project = next((p for p in dataset.projects if p.name == project_name), None)

    if not target_project:
        st.error(f"Project '{project_name}' not found!")
        return

    # 2. Create the Task Object
    new_task_id = len(target_project.tasks) + 1
    new_task = Task(
        id=new_task_id,
        name=task_text,
        tags=tags if tags else [],
        duration="unknown"
    )

    # 3. Update Data Structures
    target_project.tasks.append(new_task)

    if task_text in dataset.inbox_tasks:
        dataset.inbox_tasks.remove(task_text)

    # 4. Clear cache for the next item
    if 'current_prediction' in st.session_state:
        del st.session_state.current_prediction

    # 5. Add to history for UI feedback
    if 'history' not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, f"Moved '{task_text}' → {project_name}")


def create_project_and_move(dataset, task_text, new_project_name):
    """Creates a new project on the fly and moves the task there"""
    # Check if exists
    if any(p.name.lower() == new_project_name.lower() for p in dataset.projects):
        st.warning("Project already exists, moving there instead.")
        move_task_to_project(dataset, task_text, new_project_name)
        return

    # Create Project
    new_id = max([p.id for p in dataset.projects], default=0) + 1
    new_proj = Project(id=new_id, name=new_project_name)
    dataset.projects.append(new_proj)

    # Move Task
    move_task_to_project(dataset, task_text, new_project_name)


# --- Main Layout ---

st.title("⚡ Task Triage")

col1, col2 = st.columns([1, 2])

# --- LEFT COLUMN: Dataset Management (Context) ---
with col1:
    st.subheader("📂 Dataset")

    # Dataset Selector
    available_datasets = services['dataset_manager'].list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("Select Dataset", available_datasets)

        if st.button("Load Dataset", use_container_width=True):
            try:
                dataset = services['dataset_manager'].load_dataset(selected_dataset)
                st.session_state.dataset = dataset
                # Reset state on load
                if 'current_prediction' in st.session_state: del st.session_state.current_prediction
                if 'history' in st.session_state: del st.session_state.history
                st.success(f"Loaded {len(dataset.inbox_tasks)} inbox tasks")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("No datasets found.")
        st.stop()

    # Show Stats / Progress
    if 'dataset' in st.session_state:
        dataset = st.session_state.dataset
        total_tasks = len(dataset.inbox_tasks) + sum(len(p.tasks) for p in dataset.projects)
        processed = sum(len(p.tasks) for p in dataset.projects)

        st.metric("Inbox Remaining", len(dataset.inbox_tasks))
        st.progress(processed / total_tasks if total_tasks > 0 else 0)

        # Save Controls
        st.markdown("---")
        new_name = st.text_input("Save As", value=selected_dataset)
        if st.button("💾 Save Progress", use_container_width=True):
            req = services['projector'].from_ui_state(dataset, new_name)
            res = services['save_command'].execute(req, dataset)
            if res.success:
                st.success("Saved!")
            else:
                st.error(res.message)

        # Recent History
        if 'history' in st.session_state and st.session_state.history:
            st.markdown("---")
            st.caption("Recent Actions:")
            for action in st.session_state.history[:5]:
                st.caption(f"✅ {action}")

# --- RIGHT COLUMN: The Active Task (Tinder Style) ---
with col2:
    if 'dataset' not in st.session_state:
        st.info("👈 Please load a dataset to begin.")

    elif not st.session_state.dataset.inbox_tasks:
        st.balloons()
        st.success("🎉 Inbox Zero! Great job.")
        st.markdown("You can save your dataset now in the left panel.")

    else:
        # Get the first task in the queue
        current_task_text = st.session_state.dataset.inbox_tasks[0]

        # --- AI PREDICTION ---
        # We cache the prediction so it doesn't re-run if the user interacts with other UI elements
        if 'current_prediction' not in st.session_state or st.session_state.current_task_ref != current_task_text:
            with st.spinner("🤖 AI Analyzing..."):
                prediction = analyze_single_task(
                    services['client'],
                    current_task_text,
                    [p.name for p in st.session_state.dataset.projects]
                )
                st.session_state.current_prediction = prediction
                st.session_state.current_task_ref = current_task_text  # Track which task this pred belongs to

        pred = st.session_state.current_prediction

        # --- THE CARD UI ---
        with st.container(border=True):
            st.caption("Current Task")
            st.markdown(f"### {current_task_text}")

            # AI Insight
            if pred['suggested_project'] != "Unmatched":
                st.info(
                    f"💡 Suggestion: **{pred['suggested_project']}** ({pred['confidence']:.0%})\n\n_{pred['reasoning']}_")
            else:
                st.warning(f"❓ Unsure. Reasoning: _{pred['reasoning']}_")

            st.markdown("---")

            # --- ACTIONS ---

            # 1. Primary Action: Accept AI Suggestion
            if pred['suggested_project'] != "Unmatched":
                if st.button(f"✅ Move to {pred['suggested_project']}", type="primary", use_container_width=True):
                    move_task_to_project(
                        st.session_state.dataset,
                        current_task_text,
                        pred['suggested_project'],
                        pred.get('tags')
                    )
                    st.rerun()

            # 2. Secondary Action: Manual Override
            st.markdown("**Or choose manually:**")

            # Create a grid of buttons for existing projects
            projects = st.session_state.dataset.projects

            # Split projects into rows of 3
            cols = st.columns(3)
            for i, project in enumerate(projects):
                # Skip the one we already showed as primary button
                if project.name == pred['suggested_project']:
                    continue

                if cols[i % 3].button(project.name, use_container_width=True):
                    move_task_to_project(st.session_state.dataset, current_task_text, project.name)
                    st.rerun()

            # 3. Tertiary Action: Create New Project
            st.markdown("---")
            c1, c2 = st.columns([3, 1])
            with c1:
                new_proj_name = st.text_input("New Project Name", placeholder="e.g. Vacation Planning",
                                              label_visibility="collapsed")
            with c2:
                if st.button("Create & Move", use_container_width=True):
                    if new_proj_name:
                        create_project_and_move(st.session_state.dataset, current_task_text, new_proj_name)
                        st.rerun()

            # 4. Skip / Delete
            if st.button("⏭️ Skip (Move to end)", type="secondary"):
                # Rotate list
                task = st.session_state.dataset.inbox_tasks.pop(0)
                st.session_state.dataset.inbox_tasks.append(task)
                # Clear cache
                del st.session_state.current_prediction
                st.rerun()

# Debug info (Optional, remove in prod)
# st.write(st.session_state)