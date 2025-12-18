import streamlit as st
from services.repository import ExecutionService, YamlRepository

def render_execution_view(execution_service: ExecutionService, repo: YamlRepository):
    st.title("✅ Next Actions")

    all_tags = set()
    for p in repo.data.projects:
        for t in p.tasks:
            all_tags.update(t.tags)

    # Handle case where no tags exist
    options = list(all_tags)
    selected_tag = None
    if options:
        selected_tag = st.pills("Context", options, selection_mode="single")

    tasks = execution_service.get_next_actions(context_filter=selected_tag)

    if not tasks:
        st.info("No active tasks found for this context.")
        return

    for task in tasks:
        parent_proj = repo.get_task_parent(task.id)
        proj_name = parent_proj.name if parent_proj else "Unknown"
        proj_id = parent_proj.id if parent_proj else 0

        col1, col2 = st.columns([0.5, 10])

        # Checkbox
        is_done = col1.checkbox("Done", value=False, key=f"exec_{task.id}", label_visibility="collapsed")

        if is_done:
            execution_service.complete_task(proj_id, task.id)
            st.toast(f"Completed: {task.name}")
            st.rerun()

        col2.markdown(f"**{task.name}** <span style='color:gray; font-size:0.8em'>({proj_name})</span>", unsafe_allow_html=True)
        if task.tags:
            col2.caption(f"🏷️ {', '.join(task.tags)}")