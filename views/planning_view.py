import streamlit as st
from services.repository import PlanningService
from services import TaskClassifier
from models.entities import ResourceType, TaskItem, ResourceItem, ReferenceItem
from views.components import render_item
from views.common import get_logger
from views.components import render_item, render_debug_panel
from views.common import get_logger, set_debug_state

logger = get_logger("PlanningView")


def render_planning_view(planning_service: PlanningService, classifier: TaskClassifier):
    logger.info("--- Rendering Planning View ---")
    st.title("🎯 Planning & Review")

    # --- 1. GLOBAL ACTIONS (Create Goal) ---
    with st.expander("➕ Create New Goal", expanded=False):
        with st.form("new_goal"):
            g_name = st.text_input("Goal Name")
            g_desc = st.text_area("Description")
            if st.form_submit_button("Create Goal"):
                logger.info(f"Creating new goal: {g_name}")
                planning_service.create_goal(g_name, g_desc)
                st.success("Goal created!")
                st.rerun()

    # --- 2. DATA FETCHING ---
    goals = planning_service.get_all_goals()
    all_projects = planning_service.repo.data.projects
    logger.info(f"Fetched {len(goals)} goals and {len(all_projects)} total projects.")

    # Helper to get projects for a context (Goal or None)
    def get_sorted_projects(goal_id):
        projs = [p for p in all_projects if p.goal_id == goal_id]
        # Sort by sort_order if it exists, otherwise by ID
        projs.sort(key=lambda p: getattr(p, 'sort_order', p.id))
        return projs

    # --- 3. RENDER GOALS ---
    for goal in goals:
        projects = get_sorted_projects(goal.id)
        logger.debug(f"Goal '{goal.name}' has {len(projects)} projects.")

        # Level 1: The Goal Container
        with st.expander(f"🏆 {goal.name}", expanded=True):
            if goal.description:
                st.markdown(f"<span style='color:grey; font-style:italic'>{goal.description}</span>",
                            unsafe_allow_html=True)
                st.markdown("---")

            if not projects:
                st.info("No projects linked to this goal.")

            for proj in projects:
                _render_project_strip(proj, planning_service, classifier)

    # --- 4. RENDER ORPHANED PROJECTS ---
    orphaned = get_sorted_projects(None)
    if orphaned:
        logger.debug(f"Found {len(orphaned)} orphaned projects.")
        st.markdown("#### 📂 Uncategorized Projects")
        for proj in orphaned:
            _render_project_strip(proj, planning_service, classifier)

    render_debug_panel()


def _render_project_strip(project, service: PlanningService, classifier: TaskClassifier):
    """
    Renders a project as a clean 'Strip' with a header and collapsible body.
    """
    logger.debug(f"Rendering Project Strip: {project.name} (ID: {project.id})")

    # Level 2: The Project Strip Container
    # with st.container(border=True):

    # --- A. THE HEADER ROW (Always Visible) ---
    # Layout: [ Title (70%) ] [ Up | Down | Settings (30%) ]
    col_title, col_toolbar = st.columns([0.7, 0.3], vertical_alignment="center")

    with col_title:
        st.markdown(f"#### {project.name}")
        # Optional: Show progress bar or stats here in the future

    with col_toolbar:
        # Nested columns for tight button spacing
        btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1])

        # 1. Move Up
        if btn_c1.button("⬆️", key=f"up_{project.id}", help="Move Project Up"):
            if hasattr(service, 'move_project'):
                logger.info(f"Moving project {project.id} UP")
                service.move_project(project.id, "up")
                st.rerun()

        # 2. Move Down
        if btn_c2.button("⬇️", key=f"down_{project.id}", help="Move Project Down"):
            if hasattr(service, 'move_project'):
                logger.info(f"Moving project {project.id} DOWN")
                service.move_project(project.id, "down")
                st.rerun()

        # 3. Settings (Popover)
        with btn_c3.popover("⚙️", help="Project Settings"):
            st.markdown("#### Project Settings")

            # Link to Goal Logic
            goals_list = service.get_all_goals()
            goal_options = ["None"] + [g.name for g in goals_list]

            # --- NEW: DOMAIN SELECTOR ---
            from models.entities import DomainType # Ensure import

            # Create list of options
            domain_options = [d.value for d in DomainType]

            # Current selection
            current_domain = project.domain.value if project.domain else DomainType.LIFESTYLE.value

            selected_domain_str = st.selectbox(
                "Project Domain (Vocabulary)",
                options=domain_options,
                index=domain_options.index(current_domain),
                key=f"dom_sel_{project.id}",
                help="Determines which tags the AI will use (e.g. Software vs Maker)"
            )

            # Save if changed
            if selected_domain_str != current_domain:
                new_domain_enum = DomainType(selected_domain_str)
                logger.info(f"Changing project {project.id} domain to {new_domain_enum}")
                # We need a service method for this, or direct repo update
                project.domain = new_domain_enum
                service.repo.mark_dirty() # Direct update for simplicity
                st.rerun()

            st.divider()

            # ✨ THE MAGIC BUTTON
            if st.button("✨ Auto-Enrich Items", key=f"enrich_{project.id}",
                         help="Use AI to add tags and duration to empty tasks"):
                with st.spinner(f"Enriching '{project.name}'..."):

                    result_stats, debug_info = service.enrich_project(project.id, classifier)

                    # 4. SET DEBUG STATE
                    if debug_info:
                        set_debug_state(
                            source=f"Enricher ({project.name})",
                            prompt=debug_info.get('prompt', ''),
                            response=debug_info.get('response', ''),
                            schema=debug_info.get('schema', None)
                        )

                    if result_stats > 0:
                        st.success(f"Enriched {result_stats} items!")
                        st.rerun()
                    else:
                        st.info("No items needed enrichment.")

    # --- B. THE COLLAPSIBLE BODY (Unified Stream) ---
    # Level 3: The Content
    item_count = len(project.items)
    label = f"Show {item_count} Items" if item_count > 0 else "Empty Project (Add Items)"

    # --- CALCULATE UNTAGGED COUNT ---
    # Logic: Active items (not completed) that have empty tags
    untagged_count = sum(
        1 for i in project.items
        if not getattr(i, 'is_completed', False)
        and not getattr(i, 'is_acquired', False)
        and not i.tags
    )

    # --- B. THE COLLAPSIBLE BODY ---
    item_count = len(project.items)

    # Dynamic Label Construction
    if item_count == 0:
        label = "Empty Project (Add Items)"
    else:
        label = f"Show {item_count} Items"

        if untagged_count > 0:
            label += f" | ⚠️ {untagged_count} need tags"

    with st.expander(label, expanded=False):

        # Render Items
        if not project.items:
            st.caption("No items yet.")
        else:
            logger.debug(f"Rendering {item_count} items for project {project.name}")
            # Sort items by creation date
            sorted_items = sorted(project.items, key=lambda x: x.created_at)

            for item in sorted_items:
                # Pass the completion callback!
                # We assume PlanningService has complete_item (added in previous step)
                # If not, we can use a lambda to call repo directly or ExecutionService logic
                if hasattr(service, 'complete_item'):
                    render_item(item, on_complete=service.complete_item)
                else:
                    # Fallback if method missing (should be added to service)
                    render_item(item)

        st.markdown("---")

        # --- C. QUICK ADD FOOTER ---
        # Level 4: The Quick Add
        # Using a Popover for the form keeps the list clean
        with st.popover("➕ Add Item", use_container_width=True):
            st.markdown("#### New Item")

            # 1. Select Type
            type_choice = st.radio(
                "Type",
                ["Task", "Resource", "Reference"],
                horizontal=True,
                key=f"type_{project.id}",
                label_visibility="collapsed"
            )

            # 2. Input Name
            name_input = st.text_input("Item Name", key=f"name_{project.id}", placeholder="e.g., Buy paint")

            # 3. Dynamic Fields
            extra_data = {}
            if type_choice == "Task":
                tags = st.text_input("Tags", key=f"tags_{project.id}", placeholder="physical, urgent")
                extra_data['tags'] = [t.strip() for t in tags.split(",")] if tags else []

            elif type_choice == "Resource":
                col_r1, col_r2 = st.columns(2)
                res_type = col_r1.selectbox("Category", [ResourceType.TO_BUY.value, ResourceType.TO_GATHER.value],
                                            key=f"rt_{project.id}")
                res_store = col_r2.text_input("Store", value="General", key=f"rs_{project.id}")
                extra_data['store'] = res_store
                # Note: We need to pass the Enum to the service, handled below

            elif type_choice == "Reference":
                content = st.text_area("Content / URL", key=f"ref_{project.id}")
                extra_data['content'] = content

            # 4. Submit
            if st.button("Save Item", key=f"save_{project.id}", type="primary"):
                if name_input:
                    logger.info(f"Manually adding item: {name_input} ({type_choice}) to project {project.id}")

                    service.add_manual_item(
                        project.id,
                        kind=type_choice.lower(),
                        name=name_input,
                        **extra_data
                    )
                    st.rerun()
