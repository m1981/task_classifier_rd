
import streamlit as st
import anthropic
from services import DatasetManager, PromptBuilder, ResponseParser, TaskClassifier, SaveDatasetCommand, DatasetProjector
from models import ClassificationRequest, Project
from models.dtos import SaveDatasetRequest

st.set_page_config(page_title="AI Task Classification", layout="wide")

@st.cache_resource
def get_services():
    # Initialize core services
    dataset_manager = DatasetManager()
    prompt_builder = PromptBuilder()
    response_parser = ResponseParser()
    
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    classifier = TaskClassifier(client, prompt_builder, response_parser)
    
    # Initialize command/projector services
    projector = DatasetProjector()
    save_command = SaveDatasetCommand(dataset_manager, projector)
    
    return {
        'dataset_manager': dataset_manager,
        'classifier': classifier,
        'projector': projector,
        'save_command': save_command
    }

services = get_services()

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

        # Show problematic tasks for review
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
    available_datasets = services['dataset_manager'].list_datasets()
    if available_datasets:
        selected_dataset = st.selectbox("Select Dataset", available_datasets)

        if st.button("📂 Load Dataset", use_container_width=True):
            try:
                dataset = services['dataset_manager'].load_dataset(selected_dataset)
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
        projects_text = '\n'.join([f"{p.id};{p.name}" for p in dataset.projects])
        edited_projects = st.text_area(
            "Projects (Format: ID;Name)",
            value=projects_text,
            help="Edit format: 1;Kitchen Renovation, 2;Bathroom Upgrade"
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
            new_projects = []
            
            if edited_projects != projects_text:
                # Create lookup by position/order to preserve data when names change
                original_projects_list = dataset.projects
                project_lines = [line.strip() for line in edited_projects.strip().split('\n') if line.strip()]
                
                for line in project_lines:
                    if ';' in line:
                        parts = line.split(';', 1)
                        project_id = int(parts[0].strip())
                        project_name = parts[1].strip()
                        
                        # Find original by ID (not position or name)
                        original = next((p for p in dataset.projects if p.id == project_id), None)
                        if original:
                            # Preserve all data, update name only
                            new_projects.append(Project(
                                id=project_id,
                                name=project_name,
                                status=original.status,
                                tags=original.tags,
                                tasks=original.tasks
                            ))
                    else:
                        project_name = line.strip()
                        new_projects.append(Project(
                            id=len(new_projects) + 1,
                            name=project_name,
                            status="ongoing",
                            tags=[],
                            tasks=[]
                        ))
            else:
                new_projects = dataset.projects
            
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
                # Use new command pattern
                save_request = services['projector'].from_ui_state(
                    dataset, new_dataset_name.strip()
                )
                
                try:
                    result = services['save_command'].execute(save_request, dataset)
                    if result.success:
                        st.success(result.message)
                        st.rerun()
                    else:
                        st.error(f"Save failed: {result.message}")
                except Exception as e:
                    st.error(f"Save failed: {str(e)}")

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
                        response = services['classifier'].classify(request)
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