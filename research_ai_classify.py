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

def classify_tasks(inbox_tasks: List[str], projects: List[Dict], 
                  reference_tasks: List[Dict], prompt_variant: str) -> List[Dict]:
    """Classify tasks using Anthropic Claude"""
    client = get_anthropic_client()
    
    # Build prompt based on variant
    if prompt_variant == "basic":
        prompt = f"""
        Available projects: {[p['subject'] for p in projects]}
        
        Classify these tasks: {inbox_tasks}
        
        Return JSON array with: task, suggestedProject, confidence, extractedTags, estimatedDuration, reasoning
        """
    elif prompt_variant == "detailed":
        prompt = f"""
        Reference examples:
        {json.dumps(reference_tasks, indent=2)}
        
        Available projects:
        {json.dumps(projects, indent=2)}
        
        Tasks to classify: {inbox_tasks}
        
        For each task, return JSON with:
        - task: original task text
        - suggestedProject: best matching project
        - confidence: 0-1 score
        - extractedTags: relevant tags based on examples
        - estimatedDuration: time estimate
        - reasoning: explanation
        """
    elif prompt_variant == "few-shot":
        prompt = f"""
        Here are examples of how to classify tasks:
        
        Example 1: "Mount electrical socket" → Project: "Dining room redecorated", Tags: ["physical", "electrical"], Duration: "1h"
        Example 2: "Send email to Hotel" → Project: "Birthday party", Tags: ["digital"], Duration: "15min"
        
        Available projects: {[p['subject'] for p in projects]}
        Reference patterns: {[(r['subject'], r['tags']) for r in reference_tasks[:3]]}
        
        Classify these tasks: {inbox_tasks}
        
        Return JSON array with: task, suggestedProject, confidence, extractedTags, estimatedDuration, reasoning
        """
    
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        return json.loads(response.content[0].text)
    except Exception as e:
        st.error(f"Classification failed: {e}")
        return []

# Main UI
st.title("🔬 AI Task Classification Research Tool")
st.markdown("Experiment with different AI prompts for task categorization")

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
    if reference_tasks:
        st.success(f"✅ Parsed {len(reference_tasks)} reference tasks")
    else:
        st.warning("⚠️ No reference tasks parsed")
    
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
    if projects:
        st.success(f"✅ Parsed {len(projects)} projects") 
    else:
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
        ["basic", "detailed", "few-shot"],
        index=1
    )
    
    # Classify button
    if st.button("🚀 Classify Tasks", type="primary", use_container_width=True):
        if not inbox_tasks:
            st.error("Please add tasks to classify")
        else:
            with st.spinner("🤖 AI is thinking..."):
                results = classify_tasks(inbox_tasks, projects, reference_tasks, prompt_variant)
                st.session_state.results = results
    
    # Results
    st.subheader("📊 Results")
    
    if 'results' in st.session_state and st.session_state.results:
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"📋 {result.get('task', f'Task {i+1}')}"):
                col_a, col_b = st.columns([2, 1])
                
                with col_a:
                    st.write(f"**Project:** {result.get('suggestedProject', 'Unknown')}")
                    
                    if result.get('extractedTags'):
                        tags_html = " ".join([f'<span style="background-color: #e1f5fe; padding: 2px 6px; border-radius: 12px; font-size: 12px;">{tag}</span>' 
                                            for tag in result['extractedTags']])
                        st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)
                    
                    if result.get('estimatedDuration'):
                        st.write(f"**Duration:** {result['estimatedDuration']}")
                
                with col_b:
                    confidence = result.get('confidence', 0)
                    color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                    st.metric("Confidence", f"{confidence:.0%}", delta=None)
                    st.write(color)
                
                if result.get('reasoning'):
                    st.write(f"**Reasoning:** {result['reasoning']}")
    else:
        st.info("👆 Click 'Classify Tasks' to see results")

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