import streamlit as st
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Project, Task

# --- 1. LOGGING SETUP ---
# Create a custom logger
logger = logging.getLogger("TaskFlow")
logger.setLevel(logging.DEBUG)

# Create handler to print to console (Terminal)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Avoid duplicate handlers if script re-runs
if not logger.handlers:
    logger.addHandler(handler)

def log_step(message: str, level="info"):
    """Helper to log to both Console and Streamlit Toast for visibility"""
    if level == "info":
        logger.info(message)
    elif level == "error":
        logger.error(message)
    elif level == "debug":
        logger.debug(message)

# --- 2. CORE LOGIC ---

load_dotenv()

class State:
    PROJECTS = "projects_data"
    TASKS = "tasks_data"

# --- HELPER FUNCTION ---
def flatten_data(data):
    """
    Consumes the generator/paginator and flattens nested lists.
    Handles the case where the API returns pages of results (list of lists).
    """
    # 1. Force conversion to list (consumes the generator)
    if not isinstance(data, list):
        data = list(data)

    flat_list = []
    for item in data:
        if isinstance(item, list):
            # It's a page (list of items), extend the main list
            flat_list.extend(item)
        else:
            # It's a single item, append it
            flat_list.append(item)

    return flat_list

# --- UPDATED CACHE FUNCTION ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_data(api_key: str):
    """Fetches data and ensures it is a flat list of objects."""
    log_step("Attempting to fetch data from Todoist API...", "info")
    try:
        api = TodoistAPI(api_key)

        # 1. Get Projects and Flatten
        raw_projects = api.get_projects()
        projects = flatten_data(raw_projects)
        log_step(f"API Success: Fetched {len(projects)} projects", "info")

        # 2. Get Tasks and Flatten
        raw_tasks = api.get_tasks()
        tasks = flatten_data(raw_tasks)
        log_step(f"API Success: Fetched {len(tasks)} tasks", "info")

        return projects, tasks
    except Exception as e:
        log_step(f"API FAILURE: {type(e).__name__}: {str(e)}", "error")
        raise Exception(f"Todoist API Error: {str(e)}")

def get_inbox_id(projects: List[Project]) -> Optional[str]:
    for p in projects:
        if p.is_inbox_project:
            return p.id
    # Fallback
    for p in projects:
        if p.name.lower() in ['inbox', 'skrzynka odbiorcza']:
            return p.id
    return None

def build_hierarchy(items: List[Any], parent_id_attr: str = 'parent_id', order_attr: str = 'order') -> List[Dict]:
    """Recursive tree builder with debug logging for empty states."""
    if not items:
        return []

    # Convert to dicts
    item_dicts = []
    for item in items:
        if hasattr(item, 'to_dict'):
            d = item.to_dict()
        else:
            d = item.__dict__
        item_dicts.append(d)

    item_map = {item['id']: item for item in item_dicts}
    children_map = {}
    roots = []

    for item in item_dicts:
        pid = item.get(parent_id_attr)
        if pid and pid in item_map:
            children_map.setdefault(pid, []).append(item)
        else:
            roots.append(item)

    roots.sort(key=lambda x: x.get(order_attr, 0))
    organized = []

    def traverse(item, depth, prefix, is_last):
        if depth == 0:
            current_prefix = ""
            child_prefix = ""
        else:
            current_prefix = prefix + ("└── " if is_last else "├── ")
            child_prefix = prefix + ("    " if is_last else "│   ")

        item['depth'] = depth
        item['tree_prefix'] = current_prefix
        organized.append(item)

        children = children_map.get(item['id'], [])
        children.sort(key=lambda x: x.get(order_attr, 0))

        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            traverse(child, depth + 1, child_prefix, is_last_child)

    for i, root in enumerate(roots):
        traverse(root, 0, "", i == len(roots) - 1)

    return organized

def map_tasks_to_projects(tasks: List[Task]) -> Dict[str, List[Task]]:
    mapping = {}
    for task in tasks:
        pid = task.project_id
        if pid not in mapping:
            mapping[pid] = []
        mapping[pid].append(task)
    return mapping

# --- 3. UI RENDERING ---

def render_ascii_view(projects: List[Project], tasks: List[Task]):
    log_step("Rendering ASCII View...", "debug")

    if not projects:
        st.warning("ASCII Renderer received 0 projects.")
        return

    organized_projects = build_hierarchy(projects, order_attr='child_order')
    tasks_by_project = map_tasks_to_projects(tasks)

    ascii_lines = []

    for proj in organized_projects:
        ascii_lines.append(f"{proj['tree_prefix']}{proj['name']}")
        project_tasks = tasks_by_project.get(proj['id'], [])

        if project_tasks:
            organized_tasks = build_hierarchy(project_tasks, order_attr='child_order')
            for task in organized_tasks:
                status = "✓" if task.get('is_completed') else "•"
                base_indent = " " * (len(proj['tree_prefix']) + 4)
                task_tree = task.get('tree_prefix', '')
                line = f"{base_indent}{task_tree}{status} {task['content']}"
                ascii_lines.append(line)

        ascii_lines.append("")

    final_text = "\n".join(ascii_lines)
    st.code(final_text, language="text")

def main():
    st.set_page_config(page_title="TaskFlow Debug", page_icon="🐞", layout="wide")

    # --- DEBUG PANEL ---
    with st.expander("🐞 Debug Info (Click to expand)", expanded=False):
        st.write("Python Version:", sys.version)
        st.write("Environment API Key Present:", "Yes" if os.getenv('TODOIST_API_KEY') else "No")

    st.title("✅ TaskFlow Pro (Debug Mode)")

    # Sidebar
    with st.sidebar:
        # Try to get key from env, otherwise empty
        default_key = os.getenv('TODOIST_API_KEY', '')
        api_key = st.text_input("Todoist API Key", value=default_key, type="password")

        st.divider()
        if st.button("🔄 Force Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not api_key:
        st.warning("⚠️ No API Key provided. Please enter it in the sidebar.")
        return

    # Main Logic
    try:
        with st.spinner("Syncing with Todoist..."):
            projects_raw, tasks_raw = get_cached_data(api_key)

        # --- DATA VALIDATION ---
        if not projects_raw:
            st.error("❌ API returned 0 projects. Check if your Todoist account has projects.")
            # Log raw response type for debugging
            st.write("Raw Projects Type:", type(projects_raw))
            return

        # View Selection
        view_mode = st.radio("View Mode", ["Tree Dashboard", "ASCII Export"], horizontal=True)
        st.divider()

        if view_mode == "Tree Dashboard":
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("📁 Project Structure")
                organized_projs = build_hierarchy(projects_raw, order_attr='child_order')

                if not organized_projs:
                    st.warning("Hierarchy builder returned empty list.")

                for p in organized_projs:
                    icon = "📥" if p.get('is_inbox_project') else "⭐" if p.get('is_favorite') else "📁"
                    st.text(f"{p['tree_prefix']}{icon} {p['name']}")

            with col2:
                st.subheader("📥 Inbox Quick View")
                inbox_id = get_inbox_id(projects_raw)

                if inbox_id:
                    inbox_tasks = [t for t in tasks_raw if t.project_id == inbox_id]
                    if not inbox_tasks:
                        st.info("Inbox is empty.")
                    else:
                        organized_inbox = build_hierarchy(inbox_tasks, order_attr='child_order')
                        for t in organized_inbox:
                            prio_color = {4: "🔴", 3: "🟡", 2: "🔵", 1: "⚪"}.get(t.get('priority'), "⚪")
                            st.markdown(f"{t['tree_prefix']} {prio_color} {t['content']}")
                else:
                    st.error("Could not find Inbox ID in project list.")
                    st.write("Available Projects:", [p.name for p in projects_raw])

        else:
            render_ascii_view(projects_raw, tasks_raw)

    except Exception as e:
        st.error(f"🔥 Critical Application Error: {e}")
        logger.exception("Critical Error") # Prints full stack trace to console
        if st.button("Clear Cache & Retry"):
            st.cache_data.clear()
            st.rerun()

if __name__ == "__main__":
    main()