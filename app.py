
import streamlit as st
import anthropic
from services import DatasetManager, PromptBuilder, ResponseParser, TaskClassifier
from models import ClassificationRequest, Project

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

# Results table at top (if available)
if 'response' in st.session_state and st.session_state.response.results:
    st.subheader("📊 Results")
    response = st.session_state.response

    # Enhanced results display with edge case handling
    if response.results:
        # Categorize results by confidence
        high_conf = [r for r in response.results if r.confidence >= 0.8]
        medium_conf = [r for r in response.results if 0.6 <= r.confidence < 0.8]
        low_conf = [r for r in response.results if r.confidence < 0.6]
        unmatched = [r for r in response.results if r.suggested_project.lower() == 'unmatched']

        print(f"🔍 DEBUG: Confidence breakdown - High: {len(high_conf)}, Medium: {len(medium_conf)}, Low: {len(low_conf)}, Unmatched: {len(unmatched)}")

        # Show confidence breakdown
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ High Confidence", len(high_conf), help="80%+ confidence")
        with col2:
            st.metric("⚠️ Medium Confidence", len(medium_conf), help="60-80% confidence")
        with col3:
            st.metric("❓ Low Confidence", len(low_conf), help="<60% confidence")
        with col4:
            st.metric("🔍 Unmatched", len(unmatched), help="No good project match")

        # Results table with color coding
        table_rows = ["| Task | Project | Confidence | Tags | Duration | Status |",
                     "|------|---------|------------|------|----------|--------|"]

        for result in response.results:
            tags = ', '.join(result.extracted_tags)
            duration = result.estimated_duration or 'N/A'
            confidence = f"{result.confidence:.1%}"

            # Status indicator
            if result.confidence >= 0.8:
                status = "✅ Good"
            elif result.confidence >= 0.6:
                status = "⚠️ Review"
            else:
                status = "❓ Unclear"

            table_rows.append(f"| {result.task} | {result.suggested_project} | {confidence} | {tags} | {duration} | {status} |")

        st.markdown('\n'.join(table_rows))

        # Show problematic tasks for review (combine low confidence AND unmatched)
        review_tasks = []
        for result in response.results:
            if result.confidence < 0.8 or result.suggested_project.lower() == 'unmatched':
                review_tasks.append(result)

        # Deduplicate by task name
        seen_tasks = set()
        unique_review_tasks = []
        for result in review_tasks:
            if result.task not in seen_tasks:
                seen_tasks.add(result.task)
                unique_review_tasks.append(result)
            else:
                print(f"🔍 DEBUG: Skipping duplicate task: {result.task}")

        print(f"🔍 DEBUG: Review tasks - Total: {len(review_tasks)}, Unique: {len(unique_review_tasks)}")

        if unique_review_tasks:
            with st.expander(f"🔍 Review Needed ({len(unique_review_tasks)} tasks)", expanded=False):
                for result in unique_review_tasks:
                    st.write(f"**{result.task}**")
                    st.write(f"- Suggested: {result.suggested_project} ({result.confidence:.1%})")
                    if result.alternative_projects:
                        alternatives = ', '.join(result.alternative_projects)
                        st.write(f"- Alternatives: {alternatives}")
                    st.write(f"- Reasoning: {result.reasoning}")
                    st.write("---")
else:
    st.info("👆 Load a dataset and run classification to see results table here")

# Two column layout
col1, col2 = st.columns([1, 1])

with col1:
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

        # Editable Projects
        st.markdown("**Projects**")
        projects_text = '\n'.join([f"{p.name}" for p in dataset.projects])
        edited_projects = st.text_area(
            "projects_editor",
            value=projects_text,
            height=200,
            label_visibility="collapsed"
        )

        # Editable Inbox Tasks
        st.markdown("**Inbox Tasks**")
        inbox_text = '\n'.join(dataset.inbox_tasks)
        edited_inbox = st.text_area(
            "inbox_editor",
            value=inbox_text,
            height=350,
            label_visibility="collapsed"
        )

        # Update dataset in session state when text changes
        if edited_projects != projects_text or edited_inbox != inbox_text:
            # Parse projects
            new_projects = []
            for line in edited_projects.strip().split('\n'):
                if line.strip() and ';' in line:
                    parts = line.split(';', 1)
                    new_projects.append(Project(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        status="ongoing",
                        tags=[]
                    ))
            
            # Parse inbox tasks
            new_inbox = [line.strip() for line in edited_inbox.split('\n') if line.strip()]
            
            # Update dataset
            dataset.projects = new_projects
            dataset.inbox_tasks = new_inbox
            st.session_state.dataset = dataset
        
        # Save dataset option
        st.markdown("---")
        col_save1, col_save2 = st.columns([2, 1])
        
        with col_save1:
            new_dataset_name = st.text_input(
                "Dataset name", 
                value=selected_dataset,
                placeholder="my_custom_dataset"
            )
        
        with col_save2:
            if st.button("💾 Save as Dataset", use_container_width=True):
                if new_dataset_name.strip():
                    try:
                        dataset_manager.save_dataset(new_dataset_name.strip(), dataset)
                        st.success(f"✅ Saved as '{new_dataset_name}'")
                        # Refresh available datasets
                        st.rerun()
                    except Exception as e:
                        st.error(f"Save failed: {e}")
                else:
                    st.error("Please enter a dataset name")

with col2:
    if 'dataset' in st.session_state:
        dataset = st.session_state.dataset
        
        prompt_variant = st.selectbox("Strategy", ["basic", "diy_renovation"])
        st.info("💡 Uses your current dataset with prompt template")

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