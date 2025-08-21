import streamlit as st
from models import Project, DatasetContent

# Mock data for demonstration
if 'unmatched_tasks' not in st.session_state:
    st.session_state.unmatched_tasks = [
        "Plan vacation itinerary",
        "Book hotel reservations", 
        "Research flight prices",
        "Change car oil",
        "Rotate tires",
        "Buy groceries",
        "Learn Spanish",
        "Set up home office"
    ]

if 'projects' not in st.session_state:
    st.session_state.projects = [
        Project(id=1, name="Kitchen Renovation"),
        Project(id=2, name="Bathroom Upgrade")
    ]

st.title("🔍 Create Projects from Unmatched Tasks")
st.write("Select tasks to group into new projects or create individual projects.")

# Show current unmatched tasks with checkboxes
st.subheader("📋 Unmatched Tasks")

selected_tasks = []
individual_tasks = []

# Create two columns for different selection modes
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("**Select tasks to group together:**")
    
    # Group selection checkboxes
    for i, task in enumerate(st.session_state.unmatched_tasks):
        key = f"group_{i}"
        if st.checkbox(task, key=key):
            selected_tasks.append(task)

with col2:
    st.markdown("**Or mark as individual projects:**")
    
    # Individual project checkboxes
    for i, task in enumerate(st.session_state.unmatched_tasks):
        key = f"individual_{i}"
        if st.checkbox("📁", key=key, help=f"Create '{task}' as its own project"):
            individual_tasks.append(task)

# Validation and conflict detection
conflicts = set(selected_tasks) & set(individual_tasks)
if conflicts:
    st.error(f"⚠️ Tasks cannot be both grouped and individual: {', '.join(conflicts)}")

# Action buttons section
st.markdown("---")
st.subheader("🎯 Actions")

button_col1, button_col2, button_col3 = st.columns(3)

with button_col1:
    # Group creation
    if selected_tasks and not conflicts:
        st.markdown("**Create Grouped Project:**")
        project_name = st.text_input(
            "Project name", 
            placeholder="e.g., Summer Vacation Planning",
            key="group_name"
        )
        
        if st.button("📁 Create Project with Selected", type="primary"):
            if project_name.strip():
                # Create project logic here
                new_project = Project(
                    id=len(st.session_state.projects) + 1,
                    name=project_name.strip()
                )
                st.session_state.projects.append(new_project)
                
                # Remove selected tasks from unmatched
                for task in selected_tasks:
                    st.session_state.unmatched_tasks.remove(task)
                
                st.success(f"✅ Created '{project_name}' with {len(selected_tasks)} tasks")
                st.rerun()
            else:
                st.error("Please enter a project name")
    else:
        st.markdown("*Select tasks above to enable group creation*")

with button_col2:
    # Individual project creation
    if individual_tasks and not conflicts:
        st.markdown("**Create Individual Projects:**")
        st.write(f"Will create {len(individual_tasks)} separate projects:")
        for task in individual_tasks:
            st.write(f"• {task}")
        
        if st.button("📁 Create as Individual Projects", type="secondary"):
            # Create individual projects
            for task in individual_tasks:
                new_project = Project(
                    id=len(st.session_state.projects) + 1,
                    name=task
                )
                st.session_state.projects.append(new_project)
                st.session_state.unmatched_tasks.remove(task)
            
            st.success(f"✅ Created {len(individual_tasks)} individual projects")
            st.rerun()
    else:
        st.markdown("*Mark tasks with 📁 to enable individual creation*")

with button_col3:
    # Smart suggestions
    st.markdown("**Smart Suggestions:**")
    
    # Simple keyword-based grouping suggestions
    vacation_tasks = [t for t in st.session_state.unmatched_tasks if any(word in t.lower() for word in ['vacation', 'hotel', 'flight', 'travel'])]
    car_tasks = [t for t in st.session_state.unmatched_tasks if any(word in t.lower() for word in ['car', 'oil', 'tire'])]
    
    if vacation_tasks:
        if st.button(f"🏖️ Group Vacation Tasks ({len(vacation_tasks)})"):
            st.session_state.suggested_group = vacation_tasks
            st.session_state.suggested_name = "Vacation Planning"
    
    if car_tasks:
        if st.button(f"🚗 Group Car Tasks ({len(car_tasks)})"):
            st.session_state.suggested_group = car_tasks
            st.session_state.suggested_name = "Car Maintenance"

# Show suggestions if any
if 'suggested_group' in st.session_state:
    st.info(f"💡 Suggested grouping: {', '.join(st.session_state.suggested_group)}")
    col_accept, col_reject = st.columns(2)
    
    with col_accept:
        if st.button("✅ Accept Suggestion"):
            # Apply suggestion
            new_project = Project(
                id=len(st.session_state.projects) + 1,
                name=st.session_state.suggested_name
            )
            st.session_state.projects.append(new_project)
            
            for task in st.session_state.suggested_group:
                if task in st.session_state.unmatched_tasks:
                    st.session_state.unmatched_tasks.remove(task)
            
            st.success(f"✅ Created '{st.session_state.suggested_name}' project")
            del st.session_state.suggested_group
            del st.session_state.suggested_name
            st.rerun()
    
    with col_reject:
        if st.button("❌ Reject"):
            del st.session_state.suggested_group
            del st.session_state.suggested_name
            st.rerun()

# Preview section
st.markdown("---")
st.subheader("📊 Preview")

col_preview1, col_preview2 = st.columns(2)

with col_preview1:
    st.markdown("**Current Projects:**")
    for project in st.session_state.projects:
        st.write(f"• {project.name}")

with col_preview2:
    st.markdown(f"**Remaining Unmatched ({len(st.session_state.unmatched_tasks)}):**")
    for task in st.session_state.unmatched_tasks:
        st.write(f"• {task}")

# Reset button for demo
if st.button("🔄 Reset Demo Data"):
    for key in list(st.session_state.keys()):
        if key.startswith(('group_', 'individual_', 'suggested_')):
            del st.session_state[key]
    st.session_state.unmatched_tasks = [
        "Plan vacation itinerary",
        "Book hotel reservations", 
        "Research flight prices",
        "Change car oil",
        "Rotate tires",
        "Buy groceries",
        "Learn Spanish",
        "Set up home office"
    ]
    st.session_state.projects = [
        Project(id=1, name="Kitchen Renovation"),
        Project(id=2, name="Bathroom Upgrade")
    ]
    st.rerun()