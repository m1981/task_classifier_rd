import streamlit as st
from services.repository import TriageService, YamlRepository, DraftItem
from services import TaskClassifier
from models.dtos import SingleTaskClassificationRequest
from models.ai_schemas import ClassificationType
from models.entities import SystemConfig, TaskItem
from views.common import log_action, log_state, set_debug_state
from views.components import render_debug_panel


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

    # Progress Bar
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

            # B. Prepare Tags (DB + System Defaults)
            db_tags = triage_service.get_all_tags()

            req = SingleTaskClassificationRequest(
                task_text=current_text,
                available_projects=context_str,
                existing_tags=db_tags
            )

            # 2. Get Classification
            response = classifier.classify_single(req)
            result = response.results[0]

            # 3. Create Draft
            draft = triage_service.create_draft(current_text, result)

            # 4. Store in Session
            st.session_state.current_draft = draft
            st.session_state.draft_source = current_text

            # 5. SET GLOBAL DEBUG STATE (New Pattern)
            set_debug_state(
                source="Triage",
                prompt=response.prompt_used,
                response=response.raw_response,
                schema=response.tool_schema
            )

            log_action("DRAFT CREATED", f"{result.classification_type} -> {result.suggested_project}")

    draft: DraftItem = st.session_state.current_draft
    result = draft.classification

    # ============================================================
    # 🛡️ ERROR HANDLING BLOCK
    # ============================================================
    if result.suggested_project == "SystemError" or result.reasoning.startswith("AI Error"):
        with st.container(border=True):
            st.error("🔌 Connection Failed")
            st.markdown(f"**Error Details:** `{result.reasoning}`")

            st.info("The AI could not analyze this item. You can try again or process it manually.")

            col_retry, col_manual = st.columns(2)

            with col_retry:
                if st.button("🔄 Retry AI Analysis", use_container_width=True):
                    _clear_draft_state()
                    st.rerun()

            with col_manual:
                if st.button("📝 Process Manually", use_container_width=True):
                    # Reset to clean state for manual entry
                    draft.classification.suggested_project = "Unmatched"
                    draft.classification.reasoning = "Manual override due to connection error."
                    draft.classification.confidence = 1.0
                    st.rerun()

        # Render debug panel even on error so we can see what happened
        render_debug_panel()
        return
        # ============================================================

    # --- 4. THE PROPOSAL CARD ---
    with st.container(border=True):

        # --- 1. EDITABLE TITLE (Refined Text) ---
        is_low_confidence = result.confidence < 0.8
        if is_low_confidence:
            st.warning(f"⚠️ Low Confidence ({result.confidence:.2f}). Please verify translation/project.")

        default_text = result.refined_text or current_text

        edited_text = st.text_input(
            "Task Name",
            value=default_text,
            key=f"title_{hash(current_text)}",
            help="AI translated/refined text. Edit to correct."
        )

        # Update Draft immediately if changed
        if edited_text != result.refined_text:
            draft.classification.refined_text = edited_text

        if edited_text != current_text:
            st.caption(f"Original: *{current_text}*")

        # --- B. TYPE EDITOR (Pills) ---
        type_mapping = {
            "⚡ Task": ClassificationType.TASK,
            "🛒 Resource": ClassificationType.SHOPPING,
            "📚 Reference": ClassificationType.REFERENCE,
            "✨ Project": ClassificationType.NEW_PROJECT,
            "💤 Incubate": ClassificationType.INCUBATE
        }

        current_enum = draft.classification.classification_type
        default_label = next((k for k, v in type_mapping.items() if v == current_enum), "⚡ Task")

        selected_type_label = st.pills(
            "Type",
            options=list(type_mapping.keys()),
            default=default_label,
            selection_mode="single",
            key=f"type_pills_{hash(current_text)}"
        )

        if selected_type_label:
            new_enum = type_mapping[selected_type_label]
            if new_enum != draft.classification.classification_type:
                draft.classification.classification_type = new_enum
                st.rerun()

        st.markdown(f"**Goes to ➝** **{result.suggested_project}**")

        # --- TAG EDITOR ---
        def add_new_tag():
            key = f"new_tag_{hash(current_text)}"
            new_val = st.session_state.get(key, "").strip()
            if new_val:
                if new_val not in draft.classification.extracted_tags:
                    draft.classification.extracted_tags.append(new_val)
                st.session_state[key] = ""

        db_tags = triage_service.get_all_tags()
        system_tags = SystemConfig.DEFAULT_TAGS
        all_options = list(set(db_tags + system_tags + draft.classification.extracted_tags))
        all_options.sort()

        selected_tags = st.multiselect(
            "Tags",
            options=all_options,
            default=draft.classification.extracted_tags,
            key=f"tag_editor_{hash(current_text)}",
            placeholder="Select context, energy, effort..."
        )

        if selected_tags != draft.classification.extracted_tags:
            draft.classification.extracted_tags = selected_tags

        st.text_input(
            "➕ Create new tag",
            key=f"new_tag_{hash(current_text)}",
            on_change=add_new_tag,
            placeholder="Type new tag and hit Enter"
        )

        # --- NOTES EDITOR ---
        st.caption("📝 Notes")
        notes_input = st.text_area(
            "Notes",
            value=draft.classification.notes,
            key=f"notes_{hash(current_text)}",
            placeholder="Add details, links, or sub-tasks...",
            height=100,
            label_visibility="collapsed"
        )

        if notes_input != draft.classification.notes:
            draft.classification.notes = notes_input

        # --- DURATION EDITOR (Pills) ---
        duration_options = SystemConfig.ALLOWED_DURATIONS
        default_selection = result.estimated_duration if result.estimated_duration in duration_options else None

        selected_duration = st.pills(
            "Estimated Duration",
            options=duration_options,
            default=default_selection,
            selection_mode="single",
            key=f"duration_{hash(current_text)}"
        )

        if selected_duration:
            draft.classification.estimated_duration = selected_duration
        elif result.estimated_duration and result.estimated_duration not in duration_options:
            st.caption(f"Custom AI Estimate: {result.estimated_duration}")

        # --- ACTIONS ---
        col_confirm, col_skip, col_trash = st.columns([2, 1, 1])

        with col_confirm:
            if result.classification_type == ClassificationType.NEW_PROJECT:
                st.info("👇 Review New Project details below")
            elif result.suggested_project != "Unmatched":
                if st.button("✅ Confirm", type="primary", use_container_width=True):
                    # FINAL SYNC: Ensure draft has latest values from widgets before applying
                    if edited_text: draft.classification.refined_text = edited_text
                    if selected_tags: draft.classification.extracted_tags = selected_tags
                    if selected_duration: draft.classification.estimated_duration = selected_duration
                    if notes_input: draft.classification.notes = notes_input

                    triage_service.apply_draft(draft)
                    _clear_draft_state()
                    st.rerun()
            else:
                st.warning("👇 Select a project below")

        with col_skip:
            if st.button("⏭️ Skip", use_container_width=True):
                triage_service.skip_inbox_item(current_text)
                _clear_draft_state()
                st.rerun()

        with col_trash:
            if st.button("🗑️ Trash", use_container_width=True, type="secondary"):
                log_action("TRASH", current_text)
                triage_service.delete_inbox_item(current_text)
                _clear_draft_state()
                st.rerun()

    # --- ALTERNATIVE PROJECTS (PILLS) ---
    if result.alternative_projects:
        st.caption("Or move to...")
        alts = result.alternative_projects[:3]
        cols = st.columns(len(alts))
        for i, proj_name in enumerate(alts):
            if cols[i].button(proj_name, key=f"alt_{i}", use_container_width=True):
                proj = repo.find_project_by_name(proj_name)
                if proj:
                    triage_service.move_inbox_item_to_project(current_text, proj.id, result.extracted_tags)
                    _clear_draft_state()
                    st.rerun()

    # --- MANUAL OVERRIDE & NEW PROJECT ---
    all_projs = [p.name for p in repo.data.projects]
    selected_proj = st.selectbox("All projects", all_projs, index=None, placeholder="Select project...")

    if selected_proj and st.button("Move to Selected Project"):
        target_id = repo.find_project_by_name(selected_proj).id

        # FIX: Use apply_draft to preserve AI data (Notes/Tags/Type) even on manual move
        # Sync widgets first
        if edited_text: draft.classification.refined_text = edited_text
        if selected_tags: draft.classification.extracted_tags = selected_tags
        if notes_input: draft.classification.notes = notes_input

        triage_service.apply_draft(draft, override_project_id=target_id)
        _clear_draft_state()
        st.rerun()

    is_new_proj_suggestion = (result.classification_type == ClassificationType.NEW_PROJECT)

    with st.expander("➕ Create New Project", expanded=is_new_proj_suggestion):
        with st.form(key="create_form", clear_on_submit=True, border=False):
            c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")
            default_name = result.suggested_new_project_name or ""
            new_proj_name = c_input.text_input("New Project Name", value=default_name)

            if c_btn.form_submit_button("Create & Move"):
                if new_proj_name:
                    log_action("CREATE PROJECT", new_proj_name)
                    triage_service.create_project_from_inbox(current_text, new_proj_name)
                    _clear_draft_state()
                    st.rerun()

    # --- GLOBAL DEBUG PANEL ---
    render_debug_panel()


def _clear_draft_state():
    if 'current_draft' in st.session_state: del st.session_state.current_draft
    if 'draft_source' in st.session_state: del st.session_state.draft_source
    # Note: We do NOT clear 'last_debug_event' here so the user can inspect what just happened