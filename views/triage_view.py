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
            # 1. Prepare Context
            context_str = triage_service.build_full_context_tree()

            existing_tags = triage_service.get_all_tags()

            req = SingleTaskClassificationRequest(
                task_text=current_text,
                available_projects=context_str,
                existing_tags=existing_tags
            )

            # 2. Get Classification
            response = classifier.classify_single(req)
            result = response.results[0]

            # 3. Create Draft
            draft = triage_service.create_draft(current_text, result)

            # 4. Store in Session
            st.session_state.current_draft = draft
            st.session_state.draft_source = current_text
            st.session_state.last_raw_response = response
            log_action("DRAFT CREATED", f"{result.classification_type} -> {result.suggested_project}")

    draft: DraftItem = st.session_state.current_draft
    result = draft.classification

    # --- LOGIC: DETERMINE FLOW ---
    # We treat it as a "Creation Flow" if:
    # 1. It's explicitly a NEW_PROJECT type
    # 2. It's INCUBATE type but Unmatched (implies we need a Someday/Maybe project)
    is_creation_flow = (
        result.classification_type == ClassificationType.NEW_PROJECT or
        (result.classification_type == ClassificationType.INCUBATE and result.suggested_project == "Unmatched")
    )

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
        st.markdown(f"**Project:** {result.suggested_project}")
        st.caption(f"💡 {result.reasoning}")

        if result.estimated_duration:
            st.caption(f"⏱️ Est: {result.estimated_duration}")

        # --- ACTIONS ---
        col_confirm, col_skip, col_trash = st.columns([2, 1, 1])

        # 1. CONFIRM BUTTON LOGIC
        with col_confirm:
            # CASE A: Creation Flow (New Project or Incubate->New)
            if is_creation_flow:
                st.info("👇 Review New Project details below")

            # CASE B: Standard Move (Only if matched)
            elif result.suggested_project != "Unmatched":
                # Verify project exists
                if repo.find_project_by_name(result.suggested_project):
                    if st.button("✅ Confirm", type="primary", use_container_width=True):
                        triage_service.apply_draft(draft)
                        _clear_draft_state()
                        st.rerun()
                else:
                    st.error(f"Project '{result.suggested_project}' not found!")

            # CASE C: Unmatched (Task/Resource)
            else:
                st.warning("👇 Select a project below")

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

    # --- ALTERNATIVE PROJECTS (PILLS) - Requirement 2 ---
    if result.alternative_projects:
        st.caption("Or move to...")
        # Create columns for pills to keep them compact
        # We limit to 3 to avoid layout breaking
        alts = result.alternative_projects[:3]
        cols = st.columns(len(alts))
        for i, proj_name in enumerate(alts):
            if cols[i].button(proj_name, key=f"alt_{i}", use_container_width=True):
                # Find project ID
                proj = repo.find_project_by_name(proj_name)
                if proj:
                    triage_service.move_inbox_item_to_project(current_text, proj.id, result.extracted_tags)
                    _clear_draft_state()
                    st.rerun()

    # --- MANUAL OVERRIDE & NEW PROJECT ---
    st.divider()

    # 1. Project Selector (Manual)
    all_projs = [p.name for p in repo.data.projects]
    selected_proj = st.selectbox("Manual Assignment", all_projs, index=None, placeholder="Select project...")

    if selected_proj and st.button("Move to Selected Project"):
        target_id = repo.find_project_by_name(selected_proj).id
        triage_service.move_inbox_item_to_project(current_text, target_id, [])
        _clear_draft_state()
        st.rerun()

    # 2. Create New Project (Unified)
    with st.expander("➕ Create New Project", expanded=is_creation_flow):
        with st.form(key="create_form", clear_on_submit=True, border=False):
            c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")

            # Determine Default Name
            default_name = ""
            if result.suggested_new_project_name:
                default_name = result.suggested_new_project_name
            elif result.classification_type == ClassificationType.INCUBATE:
                default_name = "Someday/Maybe"

            new_proj_name = c_input.text_input("New Project Name", value=default_name)

            if c_btn.form_submit_button("Create & Move"):
                if new_proj_name:
                    log_action("CREATE PROJECT", new_proj_name)
                    triage_service.create_project_from_inbox(current_text, new_proj_name)
                    _clear_draft_state()
                    st.rerun()

    # --- DEBUG SECTION ---
    st.markdown("---")
    with st.expander("🛠️ Debug Info"):
        if 'last_raw_response' in st.session_state:
            resp = st.session_state.last_raw_response

            st.markdown("**1. Exact Prompt Sent:**")
            # st.code preserves exact whitespace, newlines, and the ``` blocks
            st.code(resp.prompt_used, language='markdown')

            st.markdown("**2. Raw AI Response:**")
            st.code(resp.raw_response, language='json')
        else:
            st.info("No AI request made yet.")

def _clear_draft_state():
    if 'current_draft' in st.session_state: del st.session_state.current_draft
    if 'draft_source' in st.session_state: del st.session_state.draft_source
    if 'last_raw_response' in st.session_state: del st.session_state.last_raw_response