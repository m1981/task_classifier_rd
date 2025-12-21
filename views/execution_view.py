import streamlit as st
from services.repository import ExecutionService, YamlRepository
from services.analytics_service import AnalyticsService


def render_execution_view(execution_service: ExecutionService, analytics_service: AnalyticsService,
                          repo: YamlRepository):
    st.title("✅ Next Actions")

    # --- 1. SMART CONTEXT (AI Filter) ---
    with st.expander("🤖 Smart Context (Ask AI)", expanded=False):
        with st.form("smart_filter"):
            col1, col2 = st.columns([4, 1])
            query = col1.text_input("What's your context?", placeholder="e.g., 'I have 30 mins and low energy'")
            if col2.form_submit_button("Filter"):
                if query:
                    with st.spinner("AI is finding tasks..."):
                        results = analytics_service.smart_filter_tasks(query)
                        st.session_state.smart_results = results
                        st.session_state.smart_query = query
                        st.rerun()

    # --- 2. DETERMINE SOURCE (AI vs Standard) ---
    tasks = []
    is_filtered_view = False

    # Check if we have active AI results
    if 'smart_results' in st.session_state and st.session_state.smart_results:
        tasks = st.session_state.smart_results
        is_filtered_view = True
        st.info(f"🔍 Showing results for: **{st.session_state.smart_query}**")
        if st.button("Clear Filter"):
            del st.session_state.smart_results
            del st.session_state.smart_query
            st.rerun()
    else:
        # Standard Tag Filter
        all_tags = set()
        for p in repo.data.projects:
            for item in p.items:
                if hasattr(item, 'tags'):
                    all_tags.update(item.tags)

        selected_tag = None
        if all_tags:
            selected_tag = st.pills("Context", list(all_tags), selection_mode="single")

        tasks = execution_service.get_next_actions(context_filter=selected_tag)

    # --- 3. RENDER TASKS ---
    if not tasks:
        st.info("No active tasks found.")
        return

    for task in tasks:
        # Find parent project name (inefficient but simple for MVP)
        parent_name = "Unknown"
        for p in repo.data.projects:
            if task in p.items:
                parent_name = p.name
                break

        col1, col2 = st.columns([0.5, 10])

        is_done = col1.checkbox("", value=False, key=f"exec_{task.id}")
        if is_done:
            execution_service.complete_item(task.id)
            st.toast(f"Completed: {task.name}")
            # If in AI view, we might want to remove it from the cached list too
            if is_filtered_view:
                st.session_state.smart_results = [t for t in st.session_state.smart_results if t.id != task.id]
            st.rerun()

        col2.markdown(f"**{task.name}** <span style='color:gray'>({parent_name})</span>", unsafe_allow_html=True)
        if task.duration != "unknown":
            col2.caption(f"⏱️ {task.duration}")