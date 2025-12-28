import streamlit as st
from services.repository import TriageService, YamlRepository
from services import TaskClassifier
from models.dtos import SingleTaskClassificationRequest
from views.common import log_action, log_state

def render_triage_view(triage_service: TriageService, classifier: TaskClassifier, repo: YamlRepository):
    st.title("📥 Inbox Triage")

    # 1. Quick Capture (Collapsed by default)
    with st.expander("⚡ Quick Capture", expanded=False):
        # Added border=False here
        with st.form("quick_capture", clear_on_submit=True, border=False):
            c1, c2 = st.columns([4, 1])
            new_task = c1.text_input("Capture thought...", placeholder="e.g., Buy milk")
            if c2.form_submit_button("Capture"):
                if new_task:
                    log_action("CAPTURE", new_task)
                    triage_service.add_to_inbox(new_task)
                    st.rerun()

    # 2. Process Inbox
    inbox_items = triage_service.get_inbox_items()
    log_state("Current Inbox", inbox_items)

    if not inbox_items:
        st.success("🎉 Inbox Zero! You are all caught up.")
        st.balloons()
        return

    # Progress Bar - Count TaskItems from unified stream
    from models.entities import TaskItem
    total_tasks = len(inbox_items) + sum(
        len([item for item in p.items if isinstance(item, TaskItem)])
        for p in repo.data.projects
    )
    st.progress((total_tasks - len(inbox_items)) / total_tasks if total_tasks > 0 else 1.0)

    current_task_text = inbox_items[0]

    # AI Prediction (Cached in Session State)
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
            if result.extracted_tags:
                st.caption(f"Tags: {', '.join(result.extracted_tags)}")
        else:
            st.warning("❓ Unsure where to put this.")
            st.caption(f"Reasoning: {result.reasoning}")

        # --- ACTION BUTTONS (Add & Skip Side-by-Side) ---
        col_add, col_skip = st.columns([1, 1])

        # Button 1: ADD (Only if matched)
        with col_add:
            if result.suggested_project != "Unmatched":
                target_proj = next((p for p in repo.data.projects if p.name == result.suggested_project), None)
                if st.button("Add", type="primary", use_container_width=True):
                    if target_proj:
                        log_action("ADD TASK", f"{current_task_text} -> {target_proj.name}")
                        triage_service.move_inbox_item_to_project(current_task_text, target_proj.id, result.extracted_tags)
                        st.rerun()
            else:
                # Placeholder to keep alignment if needed, or leave empty
                st.empty()

        # Button 2: SKIP (Always available)
        with col_skip:
            if st.button("⏭️ Skip", use_container_width=True):
                log_action("SKIP CLICKED", current_task_text)
                triage_service.skip_inbox_item(current_task_text)
                # Clear Session State
                if 'current_prediction' in st.session_state: del st.session_state.current_prediction
                if 'current_task_ref' in st.session_state: del st.session_state.current_task_ref
                st.rerun()

    # --- MANUAL SELECTION (PILLS) ---
    project_options = [p.name for p in repo.data.projects if p.name != result.suggested_project]
    selected_project = st.pills("Manual Assignment", project_options, selection_mode="single")

    if selected_project:
        log_action("MANUAL MOVE", f"{current_task_text} -> {selected_project}")
        target_id = next(p.id for p in repo.data.projects if p.name == selected_project)
        triage_service.move_inbox_item_to_project(current_task_text, target_id, [])
        st.rerun()

    # --- CREATE NEW PROJECT ---
    should_expand = (result.suggested_project == "Unmatched")
    default_new_name = ""
    if hasattr(result, 'suggested_new_project_name') and result.suggested_new_project_name:
        default_new_name = result.suggested_new_project_name

    with st.expander("➕ Create New Project", expanded=should_expand):
        with st.form(key="create_form", clear_on_submit=True, border=False):
            c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")
            new_proj_name = c_input.text_input("New Project Name", value=default_new_name, placeholder="e.g., Bedroom Paint")
            if c_btn.form_submit_button("Create & Move"):
                if new_proj_name:
                    log_action("CREATE PROJECT", new_proj_name)
                    triage_service.create_project_from_inbox(current_task_text, new_proj_name)
                    st.rerun()

    # --- DEBUG SECTION ---
    st.markdown("---")
    with st.expander("🛠️ Debug Info"):
        st.text(f"Prompt: {response_obj.prompt_used}")
        st.code(response_obj.raw_response, language='json')