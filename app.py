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

# Dataset selector
col1, col2 = st.columns([3, 1])
with col1:
    available_datasets = dataset_manager.list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("📁 Dataset", available_datasets)
    else:
        st.warning("No datasets found. Create data/datasets/{name}/ folders first.")
        st.stop()

with col2:
    if st.button("📂 Load Dataset"):
        try:
            dataset = dataset_manager.load_dataset(selected_dataset)
            st.session_state.dataset = dataset
            st.success(f"Loaded {selected_dataset}")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load: {e}")

# Show dataset info if loaded
if 'dataset' in st.session_state:
    dataset = st.session_state.dataset
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Reference Tasks", len(dataset.reference_tasks))
    with col2:
        st.metric("Projects", len(dataset.projects))
    with col3:
        st.metric("Inbox Tasks", len(dataset.inbox_tasks))
    
    # Classification controls
    col1, col2 = st.columns([2, 1])
    with col1:
        prompt_variant = st.selectbox("Prompt Strategy", ["basic", "diy_renovation"])
    
    with col2:
        if st.button("🚀 Classify Tasks", type="primary"):
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
                        st.success(f"Classified {len(response.results)} tasks")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Classification failed: {e}")

# Show results
if 'response' in st.session_state:
    response = st.session_state.response
    
    st.subheader("📊 Results")
    
    if response.results:
        # Results table
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
    
    # Debug info (expandable)
    with st.expander("🔍 Debug Info"):
        tab1, tab2 = st.tabs(["Prompt", "Raw Response"])
        
        with tab1:
            st.code(response.prompt_used, language="text")
        
        with tab2:
            st.code(response.raw_response, language="text")

else:
    st.info("👆 Load a dataset and run classification to see results")