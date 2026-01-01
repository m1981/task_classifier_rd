import streamlit as st
import logging
import sys
import os
import json
import time
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

# --- 1. LOGGING SETUP ---
logger = logging.getLogger("TaskFlow")
logger.setLevel(logging.DEBUG)

# Clear existing handlers to prevent duplicate printing
if logger.hasHandlers():
    logger.handlers.clear()

# Console Handler
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
logger.addHandler(handler)

def log_step(message: str, level="info"):
    """Centralized logging wrapper."""
    if level == "info": logger.info(message)
    elif level == "warning": logger.warning(message)
    elif level == "error": logger.error(message)
    elif level == "debug": logger.debug(message)

# --- 2. DATA FETCHING LAYER ---
load_dotenv()


def flatten_data(data):
    """Helper to flatten paginated responses."""
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
    log_step("🚀 Starting Todoist Sync...", "info")
    start_time = time.time()

    try:
        api = TodoistAPI(api_key)

        # Fetch in parallel logic (conceptually)
        projects = flatten_data(api.get_projects())
        log_step(f"✅ Projects loaded: {len(projects)}", "debug")

        sections = flatten_data(api.get_sections())
        log_step(f"✅ Sections loaded: {len(sections)}", "debug")

        tasks = flatten_data(api.get_tasks())
        log_step(f"✅ Tasks loaded: {len(tasks)}", "debug")

        duration = time.time() - start_time
        log_step(f"🏁 Sync complete in {duration:.2f}s", "info")

        return projects, sections, tasks
    except Exception as e:
        log_step(f"🔥 API CRITICAL FAILURE: {e}", "error")
        raise e


# --- 3. HIERARCHY BUILDER (THE BRAIN) ---

class TodoistHierarchy:
    def __init__(self, projects, sections, tasks):
        log_step("⚙️ Initializing Hierarchy Builder...", "debug")
        self.output_lines = []

        self.projects = {p.id: p for p in projects}
        self.sections = {s.id: s for s in sections}
        self.tasks = {t.id: t for t in tasks}

        # Indices
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

        self.tasks_by_parent = {}
        self.tasks_by_section = {}
        self.tasks_by_project = {}

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

        log_step("⚙️ Indexing complete.", "debug")

    def _get_order(self, obj, attr_name):
        val = getattr(obj, attr_name, None)
        if val is not None: return val
        return getattr(obj, 'order', 0)

    # --- TEXT GENERATION ---
    def generate_text_tree(self):
        log_step("📝 Generating Text Tree...", "debug")
        self.output_lines = []

        # Sort root projects
        self.root_projects.sort(key=lambda x: self._get_order(x, 'child_order'))

        for p in self.root_projects:
            self._render_project_text(p, indent=0)
            self.output_lines.append("")
        return "\n".join(self.output_lines)

    def _render_project_text(self, project, indent):
        prefix = "  " * indent
        self.output_lines.append(f"{prefix}📁 {project.name}")

        # 1. Render Project-Level Tasks (No Section)
        p_tasks = self.tasks_by_project.get(project.id, [])
        p_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in p_tasks: self._render_task_text(t, indent + 1)

        # 2. Render Sections
        p_sections = self.project_sections.get(project.id, [])
        p_sections.sort(key=lambda x: self._get_order(x, 'section_order'))
        for s in p_sections: self._render_section_text(s, indent + 1)

        # 3. Render Sub-Projects
        sub_projs = self.sub_projects.get(project.id, [])
        sub_projs.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in sub_projs: self._render_project_text(sub, indent + 1)

    def _render_section_text(self, section, indent):
        prefix = "  " * indent
        self.output_lines.append(f"{prefix}🔹 {section.name.upper()}")
        s_tasks = self.tasks_by_section.get(section.id, [])
        s_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in s_tasks: self._render_task_text(t, indent + 1)

    def _render_task_text(self, task, indent):
        prefix = "  " * indent
        status = "[x]" if task.is_completed else "[ ]"
        prio = {4: "🔴", 3: "🟡", 2: "🔵", 1: ""}.get(task.priority, "")

        content = f"{prefix}{status} {prio} {task.content}"
        if task.due:
            # Handle due date object safely
            due_str = task.due.date if hasattr(task.due, 'date') else str(task.due)
            content += f" (📅 {due_str})"

        self.output_lines.append(content)

        subtasks = self.tasks_by_parent.get(task.id, [])
        subtasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in subtasks: self._render_task_text(sub, indent + 1)

    # --- JSON GENERATION (NEW) ---
    def generate_json_structure(self):
        log_step("💾 Generating JSON Structure...", "debug")
        result = []
        self.root_projects.sort(key=lambda x: self._get_order(x, 'child_order'))
        for p in self.root_projects:
            result.append(self._build_project_dict(p))
        return result

    def _build_project_dict(self, project):
        proj_dict = {
            "type": "project",
            "id": project.id,
            "name": project.name,
            "order": self._get_order(project, 'child_order'),
            "is_favorite": project.is_favorite,
            "items": []
        }

        # 1. Tasks
        p_tasks = self.tasks_by_project.get(project.id, [])
        p_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in p_tasks:
            proj_dict["items"].append(self._build_task_dict(t))

        # 2. Sections
        p_sections = self.project_sections.get(project.id, [])
        p_sections.sort(key=lambda x: self._get_order(x, 'section_order'))
        for s in p_sections:
            proj_dict["items"].append(self._build_section_dict(s))

        # 3. Sub-projects
        sub_projs = self.sub_projects.get(project.id, [])
        sub_projs.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in sub_projs:
            proj_dict["items"].append(self._build_project_dict(sub))

        return proj_dict

    def _build_section_dict(self, section):
        sec_dict = {
            "type": "section",
            "id": section.id,
            "name": section.name,
            "order": self._get_order(section, 'section_order'),
            "items": []
        }
        s_tasks = self.tasks_by_section.get(section.id, [])
        s_tasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for t in s_tasks:
            sec_dict["items"].append(self._build_task_dict(t))
        return sec_dict

    def _build_task_dict(self, task):
        # Safe date extraction
        due_val = None
        if task.due:
            if hasattr(task.due, 'date'):
                due_val = task.due.date
            else:
                due_val = str(task.due)

        task_dict = {
            "type": "task",
            "id": task.id,
            "content": task.content,
            "is_completed": task.is_completed,
            "priority": task.priority,
            "order": self._get_order(task, 'child_order'),
            "due_date": due_val, # This might be a date object, handled by json.dumps(default=str)
            "labels": task.labels,
            "subtasks": []
        }

        subtasks = self.tasks_by_parent.get(task.id, [])
        subtasks.sort(key=lambda x: self._get_order(x, 'child_order'))
        for sub in subtasks:
            task_dict["subtasks"].append(self._build_task_dict(sub))

        return task_dict

# --- 4. MAIN APP ---

def main():
    st.set_page_config(page_title="Todoist Export", layout="wide")
    st.title("🌳 Todoist Data Exporter")

    with st.sidebar:
        api_key = st.text_input("API Key", value=os.getenv('TODOIST_API_KEY', ''), type="password")
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    if not api_key:
        st.warning("Please enter your Todoist API Key.")
        return

    try:
        # Fetch Data
        projects, sections, tasks = get_full_todoist_state(api_key)

        if not projects:
            st.warning("No projects found.")
            return

        # Process Data
        processor = TodoistHierarchy(projects, sections, tasks)

        # Create Tabs for different views
        tab1, tab2 = st.tabs(["📄 Text Tree", "💾 JSON Export"])

        with tab1:
            st.subheader("Visual Hierarchy")
            try:
                tree_text = processor.generate_text_tree()
                st.text_area("Text Output", value=tree_text, height=600)
            except Exception as e:
                st.error(f"Error generating text tree: {e}")
                logger.exception("Text Tree Generation Failed")

        with tab2:
            st.subheader("Structured JSON")
            st.info("This format is optimized for importing into other applications.")

            try:
                json_data = processor.generate_json_structure()

                # FIX: default=str handles datetime objects automatically
                json_str = json.dumps(json_data, indent=2, default=str)

                st.download_button(
                    label="📥 Download JSON File",
                    data=json_str,
                    file_name="todoist_export.json",
                    mime="application/json"
                )

                st.code(json_str, language="json")
            except Exception as e:
                st.error(f"JSON Serialization Error: {e}")
                logger.exception("JSON Generation Failed")

                # Debugging aid
                with st.expander("🐞 Debug: Inspect Raw Data"):
                    st.write("Sample Task Data:", tasks[0].__dict__ if tasks else "No tasks")

    except Exception as e:
        st.error(f"Application Error: {e}")
        logger.exception("Main Application Loop Failed")

if __name__ == "__main__":
    main()