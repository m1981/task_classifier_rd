import streamlit as st
import anthropic
from typing import List, Dict, Tuple
import json

st.set_page_config(page_title="AI Task Classification Research", layout="wide")

# Initialize Anthropic client
@st.cache_resource
def get_anthropic_client():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

def parse_reference_tasks(text: str) -> List[Dict]:
    """Parse CSV-like reference tasks"""
    tasks = []
    for line in text.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(';')
        if len(parts) >= 3:
            tasks.append({
                'id': parts[0].strip(),
                'subject': parts[1].strip(),
                'tags': [t.strip() for t in parts[2].split(',')],
                'duration': parts[3].strip() if len(parts) > 3 else None
            })
    return tasks

def parse_projects(text: str) -> List[Dict]:
    """Parse CSV-like projects"""
    projects = []
    for line in text.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(';')
        if len(parts) >= 2:
            projects.append({
                'pid': parts[0].strip(),
                'subject': parts[1].strip()
            })
    return projects

def build_prompt(inbox_tasks: List[str], projects: List[Dict], 
                reference_tasks: List[Dict], prompt_variant: str) -> str:
    """Build prompt based on variant - extracted for reuse"""
    if prompt_variant == "basic":
        projects_list = '\n'.join([f"  - {p['subject']}" for p in projects])
        tasks_list = '\n'.join([f"  - {task}" for task in inbox_tasks])

        return f"""
Act as my personal advisor and assistant. I need you to help me
organize my tasks. Please be focused to detials and understan my tagging system and projects scope.
Please first explain me how do you understnad my task and my tagging system.

Available projects:
{projects_list}

Classify these tasks:
{tasks_list}

Available tags: 
  physical, digial
  out, out  - (if physical) 
  need-material (if I migh have to buy material, ingredients, etc.) 
  need-tools (if not bare handed then require tools)

Response format:

For each task, provide on separate lines:
TASK: [original task]
PROJECT: [best matching project]
CONFIDENCE: [0.0-1.0]
TAGS: [comma-separated tags]
DURATION: [time estimate]
REASONING: [brief explanation]
---
TASK: ...
PROJECT: ...
"""

def classify_tasks(inbox_tasks: List[str], projects: List[Dict],
                  reference_tasks: List[Dict], prompt_variant: str) -> Tuple[List[Dict], str, str]:
    """Classify tasks using Anthropic Claude"""
    client = get_anthropic_client()
    
    prompt = build_prompt(inbox_tasks, projects, reference_tasks, prompt_variant)
    
    with st.expander("👁️ View Current Prompt", expanded=False):
        st.code(prompt.strip(), language="text")
        st.caption(f"Strategy: {prompt_variant} | Characters: {len(prompt)}")
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_response = response.content[0].text
        # Parse multiline text response
        parsed_results = parse_multiline_response(raw_response)
        return parsed_results, prompt, raw_response
    except Exception as e:
        st.error(f"Classification failed: {e}")
        return [], prompt, str(e)

def parse_multiline_response(text: str) -> List[Dict]:
    """Parse multiline text response into structured data"""
    results = []
    current_task = {}

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if line == "---":
            if current_task:
                results.append(current_task)
                current_task = {}
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "task":
                current_task['task'] = value
            elif key == "project":
                current_task['suggestedProject'] = value
            elif key == "confidence":
                try:
                    current_task['confidence'] = float(value)
                except ValueError:
                    current_task['confidence'] = 0.5
            elif key == "tags":
                current_task['extractedTags'] = [tag.strip() for tag in value.split(',') if tag.strip()]
            elif key == "duration":
                current_task['estimatedDuration'] = value
            elif key == "reasoning":
                current_task['reasoning'] = value

    # Add last task if exists
    if current_task:
        results.append(current_task)

    return results

# Main UI
st.title("🔬 AI Task Classification Research Tool")

print(f"🐛 TOP OF APP - session_state keys: {list(st.session_state.keys())}")
if 'results' in st.session_state:
    print(f"🐛 TOP - results exists, length: {len(st.session_state.results)}")
    print(f"🐛 TOP - results content: {st.session_state.results}")
else:
    print("🐛 TOP - no results in session_state")

if 'results' in st.session_state:
    if st.session_state.results:
        print("🐛 TOP - Creating table (results exist and not empty)")
        # Create markdown table
        table_rows = ["| Task | Project | Tags | Duration |", "|------|---------|------|----------|"]
        for result in st.session_state.results:
            task_name = result.get('task', '')
            project = result.get('suggestedProject', 'Unknown')
            tags = ', '.join(result.get('extractedTags', []))
            duration = result.get('estimatedDuration', 'N/A')
            table_rows.append(f"| {task_name} | {project} | {tags} | {duration} |")
        st.markdown('\n'.join(table_rows))
    else:
        print("🐛 TOP - Results exist but empty")
        st.warning("Classification returned no results")
else:
    print("🐛 TOP - Showing info message")
    st.info("Run classification to see results table here")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Input Data")
    
    # Reference Tasks
    st.markdown("**Reference Tasks** (id;subject;tags;duration)")
    reference_text = st.text_area(
        "reference_tasks",
        value="""13;Mount electrical socket;physical,electrical;1h
14;Retouch stencils on a wall;physical,painting;1h
15;Create wall shelf;physical,carpentry;2h
16;Send email to Hotel;digital;15min
17;Prepare party list;digital;2h""",
        height=120,
        label_visibility="collapsed"
    )
    
    reference_tasks = parse_reference_tasks(reference_text)
    if reference_tasks:  # ✅ Fixed logic
        st.success(f"✅ Parsed {len(reference_tasks)} reference tasks")

    # Projects
    st.markdown("**Current Projects** (pid;subject)")
    projects_text = st.text_area(
        "projects",
        value="""3;Birthday party
5;Repair my scooter
6;Dining room redecorated""",
        height=80,
        label_visibility="collapsed"
    )
    
    projects = parse_projects(projects_text)
    if not projects:
        st.warning("⚠️ No projects parsed")
    
    # Inbox Tasks
    st.markdown("**Inbox Tasks** (one per line)")
    inbox_text = st.text_area(
        "inbox",
        value="""Buy decorations
Fix brake cable
Paint accent wall""",
        height=80,
        label_visibility="collapsed"
    )
    
    inbox_tasks = [line.strip() for line in inbox_text.split('\n') if line.strip()]
    st.caption(f"✅ {len(inbox_tasks)} tasks to classify")
    
with col2:
    st.subheader("⚙️ Classification")
    
    # Prompt variant selector
    prompt_variant = st.selectbox(
        "Prompt Strategy",
        ["basic"],
        index=0
    )

    # Classify button
    if st.button("🚀 Classify Tasks", type="primary", use_container_width=True):
        if not inbox_tasks:
            st.error("Please add tasks to classify")
        else:
            print("🐛 BUTTON CLICKED - Starting classification")
            with st.spinner("🤖 AI is thinking..."):
                results, prompt, raw_response = classify_tasks(inbox_tasks, projects, reference_tasks, prompt_variant)
                print(f"🐛 BUTTON - Got results: {results}")
                print(f"🐛 BUTTON - Results length: {len(results)}")
                st.session_state.results = results
                st.session_state.request_prompt = prompt
                st.session_state.raw_response = raw_response
                print("🐛 BUTTON - Session state updated")
                st.rerun()  # Force app to rerun and show the table

    # Show current prompt preview
    if inbox_tasks and projects:
        current_prompt = build_prompt(inbox_tasks, projects, reference_tasks, prompt_variant)
        with st.expander("👁️ Current Prompt Preview", expanded=True):
            st.code(current_prompt.strip(), language="text")
            st.caption(f"Strategy: {prompt_variant} | Characters: {len(current_prompt)}")
    else:
        st.info("Add tasks and projects to see prompt preview")
    


# Request/Response Viewer
st.subheader("🔍 Request & Response Analysis")

if 'request_prompt' in st.session_state and 'raw_response' in st.session_state:
    tab1, tab2, tab3 = st.tabs(["📤 Request", "📥 Raw Response", "✨ Pretty Response"])
    
    with tab1:
        st.markdown("**Sent to AI:**")
        st.code(st.session_state.request_prompt, language="text")
        st.caption(f"Characters: {len(st.session_state.request_prompt)}")
    
    with tab2:
        st.markdown("**Raw AI Response:**")
        st.code(st.session_state.raw_response, language="text")
        st.caption(f"Characters: {len(st.session_state.raw_response)}")
    
    with tab3:
        st.markdown("**Parsed Response:**")
        if 'results' in st.session_state and st.session_state.results:
            for i, result in enumerate(st.session_state.results, 1):
                st.markdown(f"**Task {i}:** {result.get('task', 'Unknown')}")
                st.markdown(f"- **Project:** {result.get('suggestedProject', 'Unknown')}")
                st.markdown(f"- **Confidence:** {result.get('confidence', 0):.1%}")
                st.markdown(f"- **Tags:** {', '.join(result.get('extractedTags', []))}")
                st.markdown(f"- **Duration:** {result.get('estimatedDuration', 'Unknown')}")
                st.markdown(f"- **Reasoning:** {result.get('reasoning', 'None')}")
                st.markdown("---")
        else:
            st.warning("No valid response to display")
else:
    st.info("👆 Run classification to see request/response details")

# Sidebar with metrics
with st.sidebar:
    st.header("📈 Experiment Metrics")
    
    if 'results' in st.session_state and st.session_state.results:
        results = st.session_state.results
        avg_confidence = sum(r.get('confidence', 0) for r in results) / len(results)
        
        st.metric("Tasks Classified", len(results))
        st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        st.metric("High Confidence", sum(1 for r in results if r.get('confidence', 0) > 0.8))
        
        # Export button
        if st.button("📥 Export Results"):
            st.download_button(
                "Download JSON",
                data=json.dumps(results, indent=2),
                file_name="classification_results.json",
                mime="application/json"
            )