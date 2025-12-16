import streamlit as st
from services.repository import PlanningService
from models.entities import ResourceType

def render_planning_view(planning_service: PlanningService):
    st.title("🎯 Planning & Review")

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
        tab_res, tab_ref = st.tabs(["📦 Resources", "📚 Reference"])

        with tab_res:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            res_name = c1.text_input("Item", key=f"rn_{project.id}", label_visibility="collapsed", placeholder="Item name")
            res_type = c2.selectbox("Type", [ResourceType.TO_BUY.value, ResourceType.TO_GATHER.value], key=f"rt_{project.id}", label_visibility="collapsed")
            res_store = c3.text_input("Store/Loc", key=f"rs_{project.id}", label_visibility="collapsed", placeholder="Store")

            if c4.button("➕", key=f"add_r_{project.id}"):
                r_enum = ResourceType(res_type)
                planning_service.add_resource(project.id, res_name, r_enum, res_store)
                st.rerun()

            if project.resources:
                for r in project.resources:
                    icon = "🛒" if r.type == ResourceType.TO_BUY else "🧤"
                    st.text(f"{icon} {r.name} ({r.store})")
            else:
                st.caption("No resources needed yet.")

        with tab_ref:
            c1, c2 = st.columns([5, 1])
            ref_name = c1.text_input("Ref Note", key=f"refn_{project.id}", label_visibility="collapsed")
            if c2.button("➕", key=f"add_ref_{project.id}"):
                planning_service.add_reference_item(project.id, ref_name, "")
                st.rerun()
            for ref in project.reference_items:
                st.text(f"📄 {ref.name}")

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