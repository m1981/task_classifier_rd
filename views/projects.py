import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

# Load environment variables
load_dotenv()

# Cache configuration
CACHE_DURATION_HOURS = 24
CACHE_FILE = "projects_cache.json"


def load_cache():
    """Load projects from local cache file"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                cache_time = datetime.fromisoformat(cache_data['timestamp'])

                # Check if cache is still valid
                if datetime.now() - cache_time < timedelta(hours=CACHE_DURATION_HOURS):
                    return cache_data['projects']
    except Exception as e:
        st.error(f"Error loading cache: {e}")
    return None


def save_cache(projects):
    """Save projects to local cache file"""
    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'projects': projects
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving cache: {e}")


def fetch_projects(api):
    """Fetch projects from Todoist API"""
    try:
        projects_raw = api.get_projects()
        projects = []

        # Convert to list and flatten if needed
        all_projects = list(projects_raw)
        flattened_projects = []
        for item in all_projects:
            if isinstance(item, list):
                flattened_projects.extend(item)
            else:
                flattened_projects.append(item)

        for project in flattened_projects:
            projects.append({
                'id': project.id,
                'name': project.name,
                'color': project.color,
                'is_favorite': project.is_favorite,
                'is_inbox_project': getattr(project, 'inbox_project', False),  # Fixed attribute name
                'parent_id': project.parent_id,
                'order': getattr(project, 'child_order', 0) or 0,  # Fixed order field
                'comment_count': getattr(project, 'comment_count', 0)
            })

        return projects
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def find_inbox_project_id(api) -> Optional[str]:
    """Find inbox project ID using correct API attributes"""
    try:
        projects_raw = api.get_projects()

        # Flatten nested project lists if needed
        flattened_projects = []
        all_projects = list(projects_raw)

        for item in all_projects:
            if isinstance(item, list):
                flattened_projects.extend(item)
            else:
                flattened_projects.append(item)

        # Detection strategies in order of reliability
        for project in flattened_projects:
            # Strategy 1: Check inbox_project attribute
            if getattr(project, 'inbox_project', False):
                return project.id

        # Strategy 2: Check is_inbox_project attribute (fallback)
        for project in flattened_projects:
            if getattr(project, 'is_inbox_project', False):
                return project.id

        # Strategy 3: Name matching (last resort)
        for project in flattened_projects:
            if hasattr(project, 'name') and project.name.lower() in ['inbox', 'skrzynka odbiorcza']:
                return project.id

        return None

    except Exception as e:
        st.error(f"Error finding inbox project: {e}")
        return None


def organize_tasks_hierarchy(tasks):
    """Organize tasks with sub-task indentation"""
    task_map = {task['id']: task for task in tasks}
    organized = []

    def add_task_with_subtasks(task, depth=0, parent_prefix=""):
        # Add indentation for sub-tasks
        if depth == 0:
            prefix = ""
            next_prefix = ""
        else:
            prefix = parent_prefix + ("  └── " if depth > 0 else "")
            next_prefix = parent_prefix + "      "

        task['depth'] = depth
        task['tree_prefix'] = prefix
        organized.append(task)

        # Add sub-tasks
        subtasks = [t for t in tasks if t.get('parent_id') == task['id']]
        subtasks.sort(key=lambda x: (x.get('child_order', 0), x['content']))

        for subtask in subtasks:
            add_task_with_subtasks(subtask, depth + 1, next_prefix)

    # Start with root tasks (no parent)
    root_tasks = [t for t in tasks if not t.get('parent_id')]
    root_tasks.sort(key=lambda x: (x.get('child_order', 0), x['content']))

    for task in root_tasks:
        add_task_with_subtasks(task, 0)

    return organized


def fetch_inbox_tasks(api):
    """Fetch tasks from inbox project with sub-task support"""
    inbox_project_id = find_inbox_project_id(api)

    if not inbox_project_id:
        st.warning("Could not identify inbox project")
        return []

    try:
        # Use filter to get only inbox tasks (more efficient)
        tasks_raw = api.get_tasks(project_id=inbox_project_id)
        all_tasks = list(tasks_raw)

        # Flatten nested task lists if needed
        flattened_tasks = []
        for item in all_tasks:
            if isinstance(item, list):
                flattened_tasks.extend(item)
            else:
                flattened_tasks.append(item)

        # Convert to our format
        inbox_tasks = []
        for task in flattened_tasks:
            inbox_tasks.append({
                'id': task.id,
                'content': task.content,
                'due': task.due.date if task.due and hasattr(task.due, 'date') else None,
                'labels': task.labels or [],
                'priority': task.priority,
                'parent_id': getattr(task, 'parent_id', None),
                'child_order': getattr(task, 'child_order', 0),
                'created_at': getattr(task, 'added_at', None)
            })

        # Organize with hierarchy
        return organize_tasks_hierarchy(inbox_tasks)

    except Exception as e:
        st.error(f"Error fetching inbox tasks: {e}")
        return []


def organize_projects_hierarchy(projects):
    """Organize projects in hierarchical structure with tree indicators"""
    project_map = {p['id']: p for p in projects}
    organized = []

    def add_project_with_children(project, depth=0, is_last=True, parent_prefix=""):
        # Add tree structure indicators
        if depth == 0:
            prefix = ""
            next_prefix = ""
        else:
            prefix = parent_prefix + ("└── " if is_last else "├── ")
            next_prefix = parent_prefix + ("    " if is_last else "│   ")

        project['depth'] = depth
        project['tree_prefix'] = prefix
        organized.append(project)

        # Add children
        children = [p for p in projects if p['parent_id'] == project['id']]
        children.sort(key=lambda x: (x['order'], x['name']))

        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            add_project_with_children(child, depth + 1, is_last_child, next_prefix)

    # Start with root projects (no parent)
    root_projects = [p for p in projects if not p['parent_id']]
    root_projects.sort(key=lambda x: (x['order'], x['name']))

    for i, project in enumerate(root_projects):
        is_last_root = (i == len(root_projects) - 1)
        add_project_with_children(project, 0, is_last_root)

    return organized


def fetch_project_tasks(api, project_id):
    """Fetch tasks for a specific project"""
    try:
        tasks_raw = api.get_tasks(project_id=project_id)
        all_tasks = list(tasks_raw)
        
        # Flatten nested task lists if needed
        flattened_tasks = []
        for item in all_tasks:
            if isinstance(item, list):
                flattened_tasks.extend(item)
            else:
                flattened_tasks.append(item)
        
        # Convert to our format
        project_tasks = []
        for task in flattened_tasks:
            project_tasks.append({
                'id': task.id,
                'content': task.content,
                'is_completed': task.is_completed,
                'due': task.due.date if task.due and hasattr(task.due, 'date') else None,
                'priority': task.priority,
                'parent_id': getattr(task, 'parent_id', None),
                'child_order': getattr(task, 'child_order', 0)
            })
        
        # Organize with hierarchy
        return organize_tasks_hierarchy(project_tasks)
        
    except Exception as e:
        st.error(f"Error fetching tasks for project {project_id}: {e}")
        return []


def render_ascii_projects_with_tasks(api, projects):
    """Render all projects with tasks in ASCII format"""
    st.subheader("📋 Projects & Tasks (ASCII View)")
    
    # Create text area for ASCII output
    ascii_output = []
    
    organized_projects = organize_projects_hierarchy(projects)
    
    for project in organized_projects:
        # Project line with tree structure
        project_line = f"{project.get('tree_prefix', '')}{project['name']}"
        ascii_output.append(project_line)
        
        # Fetch tasks for this project
        with st.spinner(f"Loading tasks for {project['name']}..."):
            tasks = fetch_project_tasks(api, project['id'])
        
        # Add tasks with 4-space indentation
        for task in tasks:
            task_prefix = "    " + ("✓ " if task.get('is_completed') else "• ")
            task_line = f"{project.get('tree_prefix', '')}{task_prefix}{task['content']}"
            
            # Add due date if present
            if task.get('due'):
                task_line += f" (due: {task['due']})"
            
            ascii_output.append(task_line)
        
        # Add empty line between projects
        ascii_output.append("")
    
    # Display in code block for proper formatting
    ascii_text = "\n".join(ascii_output)
    st.code(ascii_text, language="text")
    
    # Add copy button functionality
    if st.button("📋 Copy to Clipboard"):
        st.code(ascii_text)
        st.success("ASCII format ready to copy!")


def main():
    st.set_page_config(
        page_title="Projects - TaskFlow",
        page_icon="📁",
        layout="wide"
    )

    st.title("📁 Projects Overview")

    # Sidebar for API key and controls
    with st.sidebar:
        api_key = st.text_input(
            "Todoist API Key",
            value=os.getenv('TODOIST_API_KEY', ''),
            type="password"
        )

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            refresh_clicked = st.button("🔄 Refresh", use_container_width=True)
        with col2:
            clear_cache = st.button("🗑️ Clear Cache", use_container_width=True)

    if not api_key:
        st.warning("Please enter your Todoist API key in the sidebar")
        return

    # Clear cache if requested
    if clear_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            st.success("Cache cleared!")
            st.rerun()

    # Load projects (from cache or API)
    projects = None
    cache_used = False

    if not refresh_clicked:
        projects = load_cache()
        if projects:
            cache_used = True

    if projects is None:
        try:
            api = TodoistAPI(api_key)
            with st.spinner("Fetching projects from Todoist..."):
                projects = fetch_projects(api)
                if projects:
                    save_cache(projects)
        except Exception as e:
            st.error(f"Failed to connect to Todoist API: {e}")
            return

    if not projects:
        st.warning("No projects found")
        return

    # Display cache status
    if cache_used:
        st.info("📦 Data loaded from cache")
    else:
        st.success("🔄 Data refreshed from Todoist")

    # Organize projects hierarchically
    organized_projects = organize_projects_hierarchy(projects)

    # Display projects
    st.subheader(f"Total Projects: {len(projects)}")

    # Add view toggle
    view_mode = st.radio(
        "View Mode:",
        ["Tree View", "ASCII with Tasks"],
        horizontal=True
    )

    if view_mode == "Tree View":
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])

        with col1:
            for project in organized_projects:
                # Project icon based on type
                if project['is_inbox_project']:
                    icon = "📥"
                elif project['is_favorite']:
                    icon = "⭐"
                else:
                    icon = "📁"

                # Color indicator
                color_indicator = f"🟢" if project['color'] == 'green' else \
                    f"🔵" if project['color'] == 'blue' else \
                        f"🔴" if project['color'] == 'red' else \
                            f"🟡" if project['color'] == 'yellow' else \
                                f"🟣" if project['color'] == 'purple' else \
                                    f"🟠" if project['color'] == 'orange' else "⚪"

                # Display project with proper tree structure
                tree_prefix = project.get('tree_prefix', '')

                if tree_prefix:
                    formatted_prefix = f"`{tree_prefix}`"
                else:
                    formatted_prefix = ""

                st.markdown(f"{formatted_prefix}{icon} **{project['name']}** {color_indicator}")

        with col2:
            st.subheader("📥 Inbox Tasks")

            # Fetch and display inbox tasks
            try:
                api = TodoistAPI(api_key)
                with st.spinner("Loading inbox tasks..."):
                    inbox_tasks = fetch_inbox_tasks(api)

                if inbox_tasks:
                    for task in inbox_tasks:
                        # Priority indicator
                        priority_icon = "🔴" if task['priority'] == 4 else \
                            "🟡" if task['priority'] == 3 else \
                                "🔵" if task['priority'] == 2 else ""

                        # Due date indicator
                        due_text = f" 📅 {task['due']}" if task['due'] else ""

                        # Labels
                        labels_text = f" 🏷️ {', '.join(task['labels'])}" if task['labels'] else ""

                        # Display task
                        st.markdown(f"{priority_icon} {task['content']}{due_text}{labels_text}")
                else:
                    st.info("No inbox tasks found")

            except Exception as e:
                st.error(f"Error loading inbox tasks: {e}")

    else:  # ASCII with Tasks view
        try:
            api = TodoistAPI(api_key)
            render_ascii_projects_with_tasks(api, organized_projects)
        except Exception as e:
            st.error(f"Error loading ASCII view: {e}")


if __name__ == "__main__":
    main()