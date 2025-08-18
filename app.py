import streamlit as st
import anthropic
from services import DatasetManager, PromptBuilder, ResponseParser, TaskClassifier
from models import ClassificationRequest

st.set_page_config(page_title="AI Task Classification", layout="wide")

# Initialize services
@st.cache_resource
def get_services():
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    dataset_manager = DatasetManager()
    prompt_builder = PromptBuilder()
    parser = ResponseParser()
    classifier = TaskClassifier(client, prompt_builder, parser)
    return dataset_manager, classifier

dataset_manager, classifier = get_services()

st.title("🔬 AI Task Classification Tool")

# Results table at top (if available)
if 'response' in st.session_state and st.session_state.response.results:
    st.subheader("📊 Results")
    response = st.session_state.response
    
    # Create results table
    table_rows = ["| Task | Project | Confidence | Tags | Duration |", 
                 "|------|---------|------------|------|----------|"]
    
    for result in response.results:
        tags = ', '.join(result.extracted_tags)
        duration = result.estimated_duration or 'N/A'
        confidence = f"{result.confidence:.1%}"
        table_rows.append(f"| {result.task} | {result.suggested_project} | {confidence} | {tags} | {duration} |")
    
    st.markdown('\n'.join(table_rows))
    
    # Metrics
    avg_confidence = sum(r.confidence for r in response.results) / len(response.results)
    high_confidence = sum(1 for r in response.results if r.confidence > 0.8)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Confidence", f"{avg_confidence:.1%}")
    with col2:
        st.metric("High Confidence", high_confidence)
    with col3:
        st.metric("Total Tasks", len(response.results))
else:
    st.info("👆 Load a dataset and run classification to see results table here")

# Two column layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📁 Dataset")
    
    # Dataset selector
    available_datasets = dataset_manager.list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("Select Dataset", available_datasets)
        
        if st.button("📂 Load Dataset", use_container_width=True):
            try:
                dataset = dataset_manager.load_dataset(selected_dataset)
                st.session_state.dataset = dataset
                st.success(f"✅ Loaded {selected_dataset}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load: {e}")
    else:
        st.warning("No datasets found. Create data/datasets/{name}/ folders first.")
        st.stop()
    
    # Show dataset info if loaded
    if 'dataset' in st.session_state:
        dataset = st.session_state.dataset
        
        st.markdown("**Dataset Contents:**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Reference", len(dataset.reference_tasks))
        with col_b:
            st.metric("Projects", len(dataset.projects))
        with col_c:
            st.metric("Inbox", len(dataset.inbox_tasks))
        
        # Show projects
        with st.expander("📋 Projects", expanded=False):
            for project in dataset.projects:
                st.write(f"- {project.subject}")
        
        # Show inbox tasks
        with st.expander("📥 Inbox Tasks", expanded=False):
            for task in dataset.inbox_tasks:
                st.write(f"- {task}")

with col2:
    st.subheader("⚙️ Classification")
    
    if 'dataset' in st.session_state:
        dataset = st.session_state.dataset
        
        # Prompt variant selector
        prompt_variant = st.selectbox("Prompt Strategy", ["basic", "diy_renovation"])
        
        # Classify button
        if st.button("🚀 Classify Tasks", type="primary", use_container_width=True):
            if not dataset.inbox_tasks:
                st.error("No inbox tasks to classify")
            else:
                with st.spinner("🤖 AI is thinking..."):
                    try:
                        request = ClassificationRequest(
                            dataset=dataset,
                            prompt_variant=prompt_variant
                        )
                        response = classifier.classify(request)
                        st.session_state.response = response
                        st.success(f"✅ Classified {len(response.results)} tasks")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Classification failed: {e}")
        
        # Show current prompt preview
        builder = PromptBuilder()
        request = ClassificationRequest(dataset=dataset, prompt_variant=prompt_variant)
        current_prompt = builder.build_prompt(request)
        
        with st.expander("👁️ Current Prompt Preview", expanded=True):
            st.code(current_prompt.strip(), language="text")
            st.caption(f"Strategy: {prompt_variant} | Characters: {len(current_prompt)}")
    else:
        st.info("👆 Load a dataset first to see classification options")

# Debug section at bottom
if 'response' in st.session_state:
    st.subheader("🔍 Request & Response Analysis")
    response = st.session_state.response
    
    tab1, tab2 = st.tabs(["📤 Request", "📥 Raw Response"])
    
    with tab1:
        st.markdown("**Sent to AI:**")
        st.code(response.prompt_used, language="text")
        st.caption(f"Characters: {len(response.prompt_used)}")
    
    with tab2:
        st.markdown("**Raw AI Response:**")
        st.code(response.raw_response, language="text")
        st.caption(f"Characters: {len(response.raw_response)}")