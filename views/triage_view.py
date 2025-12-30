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
    if 'current_draft' not in st.session_state or st.session_state.get('draft_source') != current_text:
        log_action("AI PREDICTION START", current_text)
        with st.spinner("🤖 AI is analyzing..."):
            context_str = triage_service._build_hierarchy_context()

            req = SingleTaskClassificationRequest(
                task_text=current_text,
                available_projects=context_str
            )

            # 1. Get Classification
            response = classifier.classify_single(req)
            result = response.results[0]

            # 2. Create Draft (Proposal)
            draft = triage_service.create_draft(current_text, result)

            # 3. Store in Session
            st.session_state.current_draft = draft
            st.session_state.draft_source = current_text
            # Store raw response for debug view
            st.session_state.last_raw_response = response
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
            ClassificationType.INCUBATE: "💤 Incubate",
        }
        type_label = icons.get(result.classification_type, "❓ Unknown")

        st.markdown(f"**Type:** {type_label}")
        st.markdown(f"**Project:** `{result.suggested_project}`")
        st.caption(f"💡 {result.reasoning}")

        if result.estimated_duration:
            st.caption(f"⏱️ Est: {result.estimated_duration}")

        # --- ACTIONS ---
        col_confirm, col_skip, col_trash = st.columns([2, 1, 1])

        # 1. CONFIRM
        with col_confirm:
            btn_label = "✅ Confirm"
            if result.classification_type == ClassificationType.INCUBATE:
                btn_label = "💤 Incubate (Someday)"
            elif result.classification_type == ClassificationType.NEW_PROJECT:
                # Show the name the AI suggests
                proj_name = result.suggested_new_project_name or "New Project"
                btn_label = f"✨ Create Project: '{proj_name}'"

            if st.button(btn_label, type="primary", use_container_width=True):

                # CASE A: Create New Project
                if result.classification_type == ClassificationType.NEW_PROJECT:
                    new_name = result.suggested_new_project_name or current_text
                    log_action("CREATE PROJECT", new_name)
                    triage_service.create_project_from_draft(draft, new_name)
                    _clear_draft_state()
                    st.rerun()

                # CASE B: Standard Move (Task/Resource/Ref/Incubate)
                elif result.suggested_project != "Unmatched":
                    triage_service.apply_draft(draft)
                    _clear_draft_state()
                    st.rerun()

                # CASE C: Error (AI said Task but didn't pick a project)
                else:
                    st.error("AI could not match a project. Please use Manual Override below.")

        # 2. SKIP
        with col_skip:
            if st.button("⏭️ Skip", use_container_width=True):
                triage_service.skip_inbox_item(current_text)
                _clear_draft_state()
                st.rerun()

        # 3. TRASH
        with col_trash:
            if st.button("🗑️ Trash", use_container_width=True, type="secondary"):
                log_action("TRASH", current_text)
                triage_service.delete_inbox_item(current_text)
                _clear_draft_state()
                st.rerun()

    # --- MANUAL OVERRIDE ---
    st.divider()
    st.caption("Manual Override")

    # Project Override
    all_projs = [p.name for p in repo.data.projects]
    selected_proj = st.selectbox("Assign to Project", all_projs, index=None, placeholder="Select project...")

    if selected_proj and st.button("Move to Selected Project"):
        target_id = repo.find_project_by_name(selected_proj).id
        triage_service.move_inbox_item_to_project(current_text, target_id, [])
        _clear_draft_state()
        st.rerun()

    # --- CREATE NEW PROJECT - RESTORED ---
    should_expand = (result.suggested_project == "Unmatched")
    default_new_name = ""
    if hasattr(result, 'suggested_new_project_name') and result.suggested_new_project_name:
        default_new_name = result.suggested_new_project_name

    with st.expander("➕ Create New Project", expanded=should_expand):
        with st.form(key="create_form", clear_on_submit=True, border=False):
            c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")
            new_proj_name = c_input.text_input("New Project Name", value=default_new_name,
                                               placeholder="e.g., Bedroom Paint")
            if c_btn.form_submit_button("Create & Move"):
                if new_proj_name:
                    log_action("CREATE PROJECT", new_proj_name)
                    # Use the convenience method
                    triage_service.create_project_from_inbox(current_text, new_proj_name)
                    _clear_draft_state()
                    st.rerun()

    # --- DEBUG SECTION - RESTORED ---
    st.markdown("---")
    with st.expander("🛠️ Debug Info"):
        if 'last_raw_response' in st.session_state:
            resp = st.session_state.last_raw_response
            st.text(f"Prompt: {resp.prompt_used}")
            st.code(resp.raw_response, language='json')


def _clear_draft_state():
    if 'current_draft' in st.session_state: del st.session_state.current_draft
    if 'draft_source' in st.session_state: del st.session_state.draft_source
    if 'last_raw_response' in st.session_state: del st.session_state.last_raw_response