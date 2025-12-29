import streamlit as st
from services.analytics_service import AnalyticsService
from services.repository import YamlRepository
from models.entities import ProjectStatus

def render_coach_view(analytics_service: AnalyticsService, repo: YamlRepository):
    st.title("🤖 AI Coach")
    
    if not analytics_service.repo:
        st.warning("No dataset loaded.")
        return
    
    # Time Forecasting Section
    st.header("⏱️ Project Time Forecasts")
    
    active_projects = [p for p in repo.data.projects if p.status == ProjectStatus.ACTIVE]
    
    if not active_projects:
        st.info("No active projects to forecast.")
    else:
        for project in active_projects:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(project.name)
                with col2:
                    estimate = analytics_service.estimate_project_completion(project.id)
                    st.metric("Est. Time", estimate)
                
                # Show incomplete tasks count
                from models.entities import TaskItem
                incomplete = [item for item in project.items if isinstance(item, TaskItem) and not item.is_completed]
                if incomplete:
                    st.caption(f"{len(incomplete)} incomplete task(s)")
                else:
                    st.success("All tasks completed!")
    
    st.divider()
    
    # Strategic Review Section
    st.header("📊 Strategic Review")
    
    goals = repo.data.goals
    if goals:
        selected_goal = st.selectbox(
            "Select Goal to Review",
            ["All Goals"] + [g.name for g in goals],
            key="coach_goal_select"
        )
        
        goal_id = None
        if selected_goal != "All Goals":
            goal_obj = next((g for g in goals if g.name == selected_goal), None)
            if goal_obj:
                goal_id = goal_obj.id
        
        if st.button("Generate Review", type="primary"):
            with st.spinner("Analyzing your work..."):
                review = analytics_service.review_recent_work(goal_id)
                st.info(review)
    else:
        st.info("No goals defined. Create goals in Planning mode to get strategic reviews.")
    
    st.divider()
    
    # Quick Stats
    st.header("📈 Quick Stats")
    
    from models.entities import TaskItem
    all_tasks = []
    completed_tasks = []
    for project in repo.data.projects:
        for item in project.items:
            if isinstance(item, TaskItem):
                all_tasks.append(item)
                if item.is_completed:
                    completed_tasks.append(item)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tasks", len(all_tasks))
    with col2:
        st.metric("Completed", len(completed_tasks))
    with col3:
        completion_rate = (len(completed_tasks) / len(all_tasks) * 100) if all_tasks else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")

