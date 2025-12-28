import streamlit as st
from services.repository import TriageService, YamlRepository, DraftItem
from services import TaskClassifier
from models.dtos import SingleTaskClassificationRequest
from models.ai_schemas import ClassificationType
from views.common import log_action, log_state

def render_triage_view(triage_service: TriageService, classifier: TaskClassifier, repo: YamlRepository):
    st.title("📥 Inbox Triage")

    # 1. Quick Capture
    with st.expander("⚡ Quick Capture", expanded=False):
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

    current_text = inbox_items[0]

    # --- AI PREDICTION LOOP (PROPOSAL ENGINE) ---
    # We check if we have a draft for the CURRENT text
    if 'current_draft' not in st.session_state or st.session_state.get('draft_source') != current_text:
        log_action("AI PREDICTION START", current_text)
        with st.spinner("🤖 AI is analyzing..."):
            project_names = [p.name for p in repo.data.projects]
            req = SingleTaskClassificationRequest(
                task_text=current_text,
                available_projects=project_names
            )
            # 1. Get Classification
            response = classifier.classify_single(req)
            result = response.results[0]

            # 2. Create Draft (Proposal)
            draft = triage_service.create_draft(current_text, result)

            # 3. Store in Session
            st.session_state.current_draft = draft
            st.session_state.draft_source = current_text
            log_action("DRAFT CREATED", f"{result.classification_type} -> {result.suggested_project}")

    draft: DraftItem = st.session_state.current_draft
    result = draft.classification

    # --- THE PROPOSAL CARD ---
    with st.container(border=True):
        st.markdown(f"#### {current_text}")

        # Type Icon
        icons = {
            ClassificationType.TASK: "⚡ Task",
            ClassificationType.SHOPPING: "🛒 Resource",
            ClassificationType.REFERENCE: "📚 Reference",
            ClassificationType.NEW_PROJECT: "✨ New Project",
            ClassificationType.TRASH: "🗑️ Trash"
        }
        type_label = icons.get(result.classification_type, "❓ Unknown")

        st.markdown(f"**Type:** {type_label}")
        st.markdown(f"**Project:** `{result.suggested_project}`")
        st.caption(f"💡 {result.reasoning}")

        if result.estimated_duration:
            st.caption(f"⏱️ Est: {result.estimated_duration}")

        # --- ACTIONS ---
        c1, c2 = st.columns(2)

        # CONFIRM
        if c1.button("✅ Confirm Proposal", type="primary", use_container_width=True):
            if result.suggested_project != "Unmatched":
                triage_service.apply_draft(draft)
                _clear_draft_state()
                st.rerun()
            else:
                st.error("Cannot confirm 'Unmatched' project. Please select one below.")

        # SKIP
        if c2.button("⏭️ Skip", use_container_width=True):
            triage_service.skip_inbox_item(current_text)
            _clear_draft_state()
            st.rerun()

    # --- MANUAL OVERRIDE ---
    st.divider()
    st.caption("Manual Override")

    # Project Override
    all_projs = [p.name for p in repo.data.projects]
    selected_proj = st.selectbox("Assign to Project", all_projs, index=None, placeholder="Select project...")

    if selected_proj and st.button("Move to Selected Project"):
        # Manual override uses the convenience method which defaults to TaskItem
        # Or we could update the draft's project and apply it.
        # For simplicity, we use the direct move method:
        target_id = repo.find_project_by_name(selected_proj).id
        triage_service.move_inbox_item_to_project(current_text, target_id, [])
        _clear_draft_state()
        st.rerun()

def _clear_draft_state():
    if 'current_draft' in st.session_state: del st.session_state.current_draft
    if 'draft_source' in st.session_state: del st.session_state.draft_source