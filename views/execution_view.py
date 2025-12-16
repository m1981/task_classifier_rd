import streamlit as st
from services.repository import ExecutionService, YamlRepository

def render_execution_view(execution_service: ExecutionService, repo: YamlRepository):
    st.title("✅ Next Actions")

    all_tags = set()
    for p in repo.data.projects:
        for t in p.tasks:
            all_tags.update(t.tags)

    selected_tag = st.pills("Context", list(all_tags), selection_mode="single")

    tasks = execution_service.get_next_actions(context_filter=selected_tag)

    if not tasks:
        st.info("No active tasks found for this context.")

    for task in tasks:
        parent_proj = next((p for p in repo.data.projects if task in p.tasks), None)
        proj_name = parent_proj.name if parent_proj else "Unknown"

        col1, col2 = st.columns([0.5, 10])
        is_done = col1.checkbox("Done", value=False, key=f"exec_{task.id}", label_visibility="collapsed")

        if is_done:
            execution_service.complete_task(parent_proj.id, task.id)
            st.toast(f"Completed: {task.name}")
            st.rerun()

        col2.markdown(f"**{task.name}** <span style='color:gray; font-size:0.8em'>({proj_name})</span>", unsafe_allow_html=True)
        if task.tags:
            col2.caption(f"🏷️ {', '.join(task.tags)}")