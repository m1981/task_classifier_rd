import streamlit as st
from services.repository import PlanningService
from models.entities import ResourceType, TaskItem, ResourceItem, ReferenceItem

def render_planning_view(planning_service: PlanningService):
    st.title("🎯 Planning & Review")

    # Helper functions to filter unified stream
    def get_resources(project) -> list[ResourceItem]:
        return [item for item in project.items if isinstance(item, ResourceItem)]
    
    def get_references(project) -> list[ReferenceItem]:
        return [item for item in project.items if isinstance(item, ReferenceItem)]
    
    def get_tasks(project) -> list[TaskItem]:
        return [item for item in project.items if isinstance(item, TaskItem)]

    # 1. Create Goal
    with st.expander("➕ Create New Goal"):
        with st.form("new_goal"):
            g_name = st.text_input("Goal Name")
            g_desc = st.text_area("Description")
            if st.form_submit_button("Create Goal"):
                planning_service.create_goal(g_name, g_desc)
                st.success("Goal created!")
                st.rerun()

    # 2. Display Goals
    goals = planning_service.get_all_goals()
    orphaned_projects = planning_service.get_orphaned_projects()

    def render_project_details(project):
        st.markdown(f"**{project.name}**")
        
        # Goal linking
        goals_list = planning_service.get_all_goals()
        goal_options = ["None"] + [g.name for g in goals_list]
        current_goal_name = "None"
        if project.goal_id:
            current_goal = next((g for g in goals_list if g.id == project.goal_id), None)
            if current_goal:
                current_goal_name = current_goal.name
        
        selected_goal = st.selectbox(
            "Link to Goal",
            goal_options,
            index=goal_options.index(current_goal_name) if current_goal_name in goal_options else 0,
            key=f"goal_link_{project.id}"
        )
        
        if selected_goal != current_goal_name:
            if selected_goal == "None":
                planning_service.link_project_to_goal(project.id, None)
            else:
                selected_goal_obj = next((g for g in goals_list if g.name == selected_goal), None)
                if selected_goal_obj:
                    planning_service.link_project_to_goal(project.id, selected_goal_obj.id)
            st.rerun()
        
        # Unified Stream Display (chronological)
        st.subheader("Unified Stream")
        
        # Add new item form
        with st.expander("➕ Add Item", expanded=False):
            item_kind = st.radio("Item Type", ["Task", "Resource", "Reference"], key=f"kind_{project.id}")
            
            if item_kind == "Task":
                with st.form(f"add_task_{project.id}"):
                    task_name = st.text_input("Task Name", key=f"task_name_{project.id}")
                    task_tags = st.text_input("Tags (comma-separated)", key=f"task_tags_{project.id}")
                    if st.form_submit_button("Add Task"):
                        tags_list = [t.strip() for t in task_tags.split(",") if t.strip()] if task_tags else []
                        planning_service.add_manual_item(project.id, "task", task_name, tags=tags_list)
                        st.rerun()
            
            elif item_kind == "Resource":
                with st.form(f"add_resource_{project.id}"):
                    res_name = st.text_input("Resource Name", key=f"res_name_{project.id}")
                    res_type = st.selectbox("Type", [ResourceType.TO_BUY.value, ResourceType.TO_GATHER.value], key=f"res_type_{project.id}")
                    res_store = st.text_input("Store/Location", key=f"res_store_{project.id}", value="General")
                    if st.form_submit_button("Add Resource"):
                        r_enum = ResourceType(res_type)
                        planning_service.add_resource(project.id, res_name, r_enum, res_store)
                        st.rerun()
            
            elif item_kind == "Reference":
                with st.form(f"add_reference_{project.id}"):
                    ref_name = st.text_input("Reference Name", key=f"ref_name_{project.id}")
                    ref_content = st.text_area("Content/Notes", key=f"ref_content_{project.id}")
                    if st.form_submit_button("Add Reference"):
                        planning_service.add_reference_item(project.id, ref_name, ref_content)
                        st.rerun()
        
        # Display unified stream chronologically
        if project.items:
            for item in sorted(project.items, key=lambda x: x.created_at):
                if isinstance(item, TaskItem):
                    status = "✅" if item.is_completed else "⚡"
                    tags_str = f" [{', '.join(item.tags)}]" if item.tags else ""
                    st.markdown(f"{status} **{item.name}**{tags_str}")
                    if item.duration != "unknown":
                        st.caption(f"⏱️ {item.duration}")
                elif isinstance(item, ResourceItem):
                    icon = "🛒" if item.type == ResourceType.TO_BUY else "🧤"
                    acquired = "✓" if item.is_acquired else ""
                    st.markdown(f"{icon} {acquired} **{item.name}** ({item.store})")
                elif isinstance(item, ReferenceItem):
                    st.markdown(f"📚 **{item.name}**")
                    if item.content:
                        st.caption(item.content)
        else:
            st.caption("No items yet. Add items to get started.")

    for goal in goals:
        with st.expander(f"🏆 {goal.name}", expanded=True):
            st.caption(goal.description)
            projects = planning_service.get_projects_for_goal(goal.id)
            if not projects:
                st.info("No projects linked to this goal.")
            for proj in projects:
                with st.container(border=True):
                    render_project_details(proj)

    if orphaned_projects:
        with st.expander("📂 Projects without Goals", expanded=False):
            for proj in orphaned_projects:
                with st.container(border=True):
                    render_project_details(proj)