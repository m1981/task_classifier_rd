import streamlit as st
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

# --- 1. LOGGING SETUP ---
logger = logging.getLogger("TaskFlow")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)


def log_step(message: str, level="info"):
    if level == "info":
        logger.info(message)
    elif level == "error":
        logger.error(message)


# --- 2. DATA FETCHING LAYER ---
load_dotenv()


def flatten_data(data):
    """Consumes paginators and flattens list-of-lists if necessary."""
    if not isinstance(data, list):
        data = list(data)
    flat_list = []
    for item in data:
        if isinstance(item, list):
            flat_list.extend(item)
        else:
            flat_list.append(item)
    return flat_list


@st.cache_data(ttl=3600, show_spinner=False)
def get_full_todoist_state(api_key: str):
    """Fetches Projects, Sections, and Tasks in 3 API calls."""
    log_step("Syncing with Todoist...", "info")
    try:
        api = TodoistAPI(api_key)

        # 1. Projects
        projects = flatten_data(api.get_projects())
        log_step(f"Fetched {len(projects)} projects")

        # 2. Sections (NEW)
        sections = flatten_data(api.get_sections())
        log_step(f"Fetched {len(sections)} sections")

        # 3. Tasks
        tasks = flatten_data(api.get_tasks())
        log_step(f"Fetched {len(tasks)} tasks")

        return projects, sections, tasks
    except Exception as e:
        log_step(f"API Error: {e}", "error")
        raise e


# --- 3. HIERARCHY BUILDER (THE BRAIN) ---

class TodoistHierarchy:
    def __init__(self, projects, sections, tasks):
        self.output_lines = []

        # --- A. Convert to Dicts for easier access ---
        self.projects = {p.id: p for p in projects}
        self.sections = {s.id: s for s in sections}
        self.tasks = {t.id: t for t in tasks}

        # --- B. Build Indices (The "Buckets") ---

        # 1. Project Tree: Parent_ID -> [Projects]
        self.sub_projects = {}
        self.root_projects = []
        for p in projects:
            if p.parent_id:
                self.sub_projects.setdefault(p.parent_id, []).append(p)
            else:
                self.root_projects.append(p)

        # 2. Sections: Project_ID -> [Sections]
        self.project_sections = {}
        for s in sections:
            self.project_sections.setdefault(s.project_id, []).append(s)

        # 3. Task Buckets
        self.tasks_by_parent = {}  # Subtasks (parent_id exists)
        self.tasks_by_section = {}  # Section Roots (section_id exists, no parent)
        self.tasks_by_project = {}  # Project Roots (no section, no parent)

        for t in tasks:
            # If it has a parent, it's a subtask (regardless of section)
            if t.parent_id:
                self.tasks_by_parent.setdefault(t.parent_id, []).append(t)
                continue

            # If it has a section, it belongs to the section
            if t.section_id and t.section_id != "0":
                self.tasks_by_section.setdefault(t.section_id, []).append(t)
            else:
                # Otherwise, it's a root task in the project
                self.tasks_by_project.setdefault(t.project_id, []).append(t)

    def _get_order(self, obj, attr_name):
        """
        Safely gets sorting order.
        Tries specific attribute (e.g., 'child_order'), falls back to 'order', then 0.
        """
        val = getattr(obj, attr_name, None)
        if val is not None:
            return val
        return getattr(obj, 'order', 0)

    def generate_text_tree(self):
        """Entry point to generate the text."""
        self.output_lines = []

        # Sort root projects
        self.root_projects.sort(key=lambda x: self._get_order(x, 'child_order'))

        for p in self.root_projects:
            self._render_project(p, indent=0)
            self.output_lines.append("")  # Empty line between root projects

        return "\n".join(self.output_lines)

    def _render_project(self, project, indent):
        prefix = "  " * indent
        self.output_lines.append(f"{prefix}📁 {project.name}")

        # 1. Render Project-Level Tasks (No Section)
        p_tasks = self.tasks_by_project.get(project.id, [])
        p_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in p_tasks:
            self._render_task(t, indent + 1)

        # 2. Render Sections
        p_sections = self.project_sections.get(project.id, [])
        p_sections.sort(key=lambda x: self._get_order(x, 'section_order'))
        for s in p_sections:
            self._render_section(s, indent + 1)

        # 3. Render Sub-Projects
        sub_projs = self.sub_projects.get(project.id, [])
        sub_projs.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in sub_projs:
            self._render_project(sub, indent + 1)

    def _render_section(self, section, indent):
        prefix = "  " * indent
        self.output_lines.append(f"{prefix}🔹 {section.name.upper()}")

        # Render Section Tasks
        s_tasks = self.tasks_by_section.get(section.id, [])
        s_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in s_tasks:
            self._render_task(t, indent + 1)

    def _render_task(self, task, indent):
        prefix = "  " * indent
        status = "[x]" if task.is_completed else "[ ]"

        # Add priority indicator
        prio = {4: "🔴", 3: "🟡", 2: "🔵", 1: ""}.get(task.priority, "")

        content = f"{prefix}{status} {prio} {task.content}"
        if task.due:
            # Handle due date object safely
            due_str = task.due.date if hasattr(task.due, 'date') else str(task.due)
            content += f" (📅 {due_str})"

        self.output_lines.append(content)

        # Render Sub-tasks (Recursion)
        subtasks = self.tasks_by_parent.get(task.id, [])
        subtasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in subtasks:
            self._render_task(sub, indent + 1)


# --- 4. MAIN APP ---

def main():
    st.set_page_config(page_title="Todoist Full Tree", layout="wide")
    st.title("🌳 Todoist Full Hierarchy")

    with st.sidebar:
        api_key = st.text_input("API Key", value=os.getenv('TODOIST_API_KEY', ''), type="password")
        if st.button("Refresh"):
            st.cache_data.clear()
            st.rerun()

    if not api_key:
        st.warning("Enter API Key")
        return

    try:
        # Fetch Data
        projects, sections, tasks = get_full_todoist_state(api_key)

        if not projects:
            st.warning("No projects found.")
            return

        # Process Data
        processor = TodoistHierarchy(projects, sections, tasks)
        tree_text = processor.generate_text_tree()

        # Display
        st.subheader("Text Output")
        st.text_area("Copy this:", value=tree_text, height=600)

    except Exception as e:
        st.error(f"Error: {e}")


if __name__ == "__main__":
    main()