import streamlit as st
from services.repository import TriageService, YamlRepository, DraftItem
from services import TaskClassifier
from models.dtos import SingleTaskClassificationRequest
from models.ai_schemas import ClassificationType
from models.entities import SystemConfig, TaskItem
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
            # We pass this to the prompt builder so AI knows what's available

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
            st.session_state.last_raw_response = response
            log_action("DRAFT CREATED", f"{result.classification_type} -> {result.suggested_project}")

    draft: DraftItem = st.session_state.current_draft
    result = draft.classification

    # ============================================================
    # 🛡️ ERROR HANDLING BLOCK (New)
    # ============================================================
    if result.suggested_project == "SystemError" or result.reasoning.startswith("AI Error"):
        with st.container(border=True):
            st.error("🔌 Connection Failed")
            st.markdown(f"**Error Details:** `{result.reasoning}`")

            st.info("The AI could not analyze this item. You can try again or process it manually.")

            col_retry, col_manual = st.columns(2)

            with col_retry:
                if st.button("🔄 Retry AI Analysis", use_container_width=True):
                    # Clear session state to force re-run of AI logic
                    if 'current_draft' in st.session_state: del st.session_state.current_draft
                    if 'draft_source' in st.session_state: del st.session_state.draft_source
                    st.rerun()

            with col_manual:
                # Allow user to skip to manual processing (treat as simple task)
                if st.button("📝 Process Manually", use_container_width=True):
                    # Reset the draft to a clean "Task" state so the user can edit it normally
                    draft.classification.suggested_project = "Unmatched"
                    draft.classification.reasoning = "Manual override due to connection error."
                    draft.classification.confidence = 1.0  # Fake confidence to hide warning
                    st.rerun()

        # Stop execution here so we don't render the broken form
        return
        # ============================================================

    # --- 4. THE PROPOSAL CARD ---
    with st.container(border=True):

        # --- 1. EDITABLE TITLE (Refined Text) ---
        # Logic: Always allow editing, but highlight if confidence is low
        is_low_confidence = result.confidence < 0.8

        # Use the refined text (translated by AI) as default, fallback to raw text
        default_text = result.refined_text or current_text

        # The Input Field
        edited_text = st.text_input(
            "Task Name",
            value=default_text,
            key=f"title_{hash(current_text)}",
            help="AI translated/refined text. Edit to correct."
        )

        # Update Draft immediately if changed
        if edited_text != result.refined_text:
            draft.classification.refined_text = edited_text

        # Show original if translation happened
        if edited_text != current_text:
            st.caption(f"Original: *{current_text}*")
        if is_low_confidence:
            st.warning(f"⚠️ Low Confidence ({result.confidence:.2f}). Please verify translation/project.")

        st.markdown(f"Goes to -> **{result.suggested_project}**")

        # ==========================================
        # 🆕 NEW SECTION: NOTES EDITOR
        # ==========================================
        st.caption("📝 Notes")
        notes_input = st.text_area(
            "Notes",
            value=draft.classification.notes,
            key=f"notes_{hash(current_text)}",
            placeholder="Add details, links, or sub-tasks...",
            height=100, # Enough for ~3 lines of text
            label_visibility="collapsed"
        )

        # --- B. TYPE EDITOR (Pills) ---
        # Map friendly labels to internal Enum
        type_mapping = {
            "⚡ Task": ClassificationType.TASK,
            "🛒 Resource": ClassificationType.SHOPPING,
            "📚 Reference": ClassificationType.REFERENCE,
            "✨ Project": ClassificationType.NEW_PROJECT,
            "💤 Incubate": ClassificationType.INCUBATE
        }

        # Find the label that matches the current enum
        current_enum = draft.classification.classification_type # Use draft, not result, to reflect edits
        default_label = next((k for k, v in type_mapping.items() if v == current_enum), "⚡ Task")

        selected_type_label = st.pills(
            "Type",
            options=list(type_mapping.keys()),
            default=default_label,
            selection_mode="single",
            key=f"type_pills_{hash(current_text)}"
        )

        # Update Draft immediately if changed
        if selected_type_label:
            new_enum = type_mapping[selected_type_label]
            if new_enum != draft.classification.classification_type:
                draft.classification.classification_type = new_enum
                # We must rerun because changing type affects the Action Buttons logic below
                st.rerun()

        # Project Display
        st.caption(f"💡 {result.reasoning}")

        # --- TAG EDITOR ---
        # 1. Define Callback to add new tags
        def add_new_tag():
            # Get value from session state using the key
            key = f"new_tag_{hash(current_text)}"
            new_val = st.session_state.get(key, "").strip()
            if new_val:
                # Add to draft if not present
                if new_val not in draft.classification.extracted_tags:
                    draft.classification.extracted_tags.append(new_val)
                # Clear the input field
                st.session_state[key] = ""

        # 2. Prepare Options
        db_tags = triage_service.get_all_tags()
        system_tags = SystemConfig.DEFAULT_TAGS
        # Critical: Include tags currently in the draft so they don't disappear
        all_options = list(set(db_tags + system_tags + draft.classification.extracted_tags))
        all_options.sort()

        # 3. Render Multiselect (For selecting existing)
        selected_tags = st.multiselect(
            "Tags",
            options=all_options,
            default=draft.classification.extracted_tags,
            key=f"tag_editor_{hash(current_text)}",
            placeholder="Select context, energy, effort..."
        )

        # Sync removal: If user removed a tag in multiselect, update draft
        if selected_tags != draft.classification.extracted_tags:
            draft.classification.extracted_tags = selected_tags

        # 4. Render Input (For creating new)
        st.text_input(
            "➕ Create new tag",
            key=f"new_tag_{hash(current_text)}",
            on_change=add_new_tag,
            placeholder="Type new tag and hit Enter"
        )



        # Immediate Sync (Keeps session state fresh if user clicks away)
        if notes_input != draft.classification.notes:
            draft.classification.notes = notes_input
        # ==========================================

        # --- DURATION EDITOR (Pills) ---
        # Standard GTD durations
        duration_options = SystemConfig.ALLOWED_DURATIONS

        # Determine default selection
        default_selection = result.estimated_duration if result.estimated_duration in duration_options else None

        selected_duration = st.pills(
            "Estimated Duration",
            options=duration_options,
            default=default_selection,
            selection_mode="single",
            key=f"duration_{hash(current_text)}"
        )

        # Update Draft immediately
        # If user selects nothing, we keep the AI's original guess or set to unknown
        if selected_duration:
            draft.classification.estimated_duration = selected_duration
        elif result.estimated_duration and result.estimated_duration not in duration_options:
            # Keep AI's custom guess if it wasn't one of the pills
            st.caption(f"Custom AI Estimate: {result.estimated_duration}")

        # --- ACTIONS ---
        col_confirm, col_skip, col_trash = st.columns([2, 1, 1])

        # 1. CONFIRM BUTTON LOGIC
        with col_confirm:
            # Logic: If New Project, point down. If Matched, allow confirm.
            if result.classification_type == ClassificationType.NEW_PROJECT:
                st.info("👇 Review New Project details below")

            # CASE B: Standard Move (Only if matched)
            elif result.suggested_project != "Unmatched":
                if st.button("✅ Confirm", type="primary", use_container_width=True):
                    # FINAL SYNC: Ensure draft has latest values from widgets before applying
                    # This catches cases where user typed but didn't blur before clicking
                    if edited_text: draft.classification.refined_text = edited_text
                    if selected_tags: draft.classification.extracted_tags = selected_tags
                    if selected_duration: draft.classification.estimated_duration = selected_duration

                    # 🆕 SYNC NOTES
                    if notes_input is not None:
                        draft.classification.notes = notes_input

                    triage_service.apply_draft(draft)
                    _clear_draft_state()
                    st.rerun()
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
        alts = result.alternative_projects[:3] # Limit to 3
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
    # 1. Project Selector (Manual)
    all_projs = [p.name for p in repo.data.projects]
    selected_proj = st.selectbox("All projects", all_projs, index=None, placeholder="Select project...")

    if selected_proj and st.button("Move to Selected Project"):
        target_id = repo.find_project_by_name(selected_proj).id
        triage_service.move_inbox_item_to_project(current_text, target_id, result.extracted_tags)
        _clear_draft_state()
        st.rerun()

    # B. Create New Project (Unified)
    # Auto-expand if AI suggested it
    is_new_proj_suggestion = (result.classification_type == ClassificationType.NEW_PROJECT)

    with st.expander("➕ Create New Project", expanded=is_new_proj_suggestion):
        with st.form(key="create_form", clear_on_submit=True, border=False):
            c_input, c_btn = st.columns([3, 1], vertical_alignment="bottom")

            # FIX: Always try to use the suggested name if available, regardless of classification type
            default_name = result.suggested_new_project_name or ""

            new_proj_name = c_input.text_input("New Project Name", value=default_name)

            if c_btn.form_submit_button("Create & Move"):
                if new_proj_name:
                    log_action("CREATE PROJECT", new_proj_name)
                    triage_service.create_project_from_inbox(current_text, new_proj_name)
                    _clear_draft_state()
                    st.rerun()

    # --- DEBUG SECTION ---
    st.markdown("---")
    with st.expander("🛠️ Debug Info (Raw Request/Response)"):
        if 'last_raw_response' in st.session_state:
            resp = st.session_state.last_raw_response

            st.subheader("1. The Prompt (User Message)")
            st.code(resp.prompt_used, language='markdown')

            st.subheader("2. The Schema (The 'Form' sent to AI)")
            st.json(resp.tool_schema)

            st.subheader("3. The Raw Response (Filled Form)")
            st.code(resp.raw_response, language='json')
        else:
            st.info("No AI request made yet.")

def _clear_draft_state():
    if 'current_draft' in st.session_state: del st.session_state.current_draft
    if 'draft_source' in st.session_state: del st.session_state.draft_source
    if 'last_raw_response' in st.session_state: del st.session_state.last_raw_response