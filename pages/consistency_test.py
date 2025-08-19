import streamlit as st
import os
from pathlib import Path
import difflib
from services import TaskClassifier, PromptBuilder, ResponseParser, DatasetManager
from models import ClassificationRequest
import anthropic
from datetime import datetime

# Create test_results directory
test_results_dir = Path("test_results")
test_results_dir.mkdir(exist_ok=True)

def save_test_response(prompt_name: str, response_text: str, test_number: int, run_dir: Path) -> str:
    """Save individual test response to file in run directory"""
    filename = f"result_{test_number:02d}.txt"
    filepath = run_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(response_text)
    
    return str(filepath)

def create_run_directory(prompt_name: str) -> Path:
    """Create timestamped run directory"""
    timestamp = datetime.now().strftime("%m-%d_%H%M%S")
    run_dir_name = f"{prompt_name}_{timestamp}"
    run_dir = test_results_dir / run_dir_name
    run_dir.mkdir(exist_ok=True)
    return run_dir

st.set_page_config(page_title="Prompt Consistency Testing", layout="wide")

# Initialize services (reuse from main app)
@st.cache_resource
def get_test_services():
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    prompt_builder = PromptBuilder()
    parser = ResponseParser()
    classifier = TaskClassifier(client, prompt_builder, parser)
    dataset_manager = DatasetManager()
    return classifier, dataset_manager

classifier, dataset_manager = get_test_services()

def normalize_response_text(text: str) -> str:
    """Normalize response text for consistent comparison"""
    return text

def calculate_similarity_score(expected: str, actual: str) -> dict:
    """Calculate line-by-line similarity metrics"""
    expected_lines = [line.strip() for line in expected.strip().split('\n') if line.strip()]
    actual_lines = [line.strip() for line in actual.strip().split('\n') if line.strip()]
    
    # Exact line matches
    matching_lines = 0
    total_expected = len(expected_lines)
    total_actual = len(actual_lines)
    
    # Create sets for faster lookup
    expected_set = set(expected_lines)
    actual_set = set(actual_lines)
    
    # Count exact matches
    matching_lines = len(expected_set.intersection(actual_set))
    
    # Calculate metrics
    precision = matching_lines / total_actual if total_actual > 0 else 0.0
    recall = matching_lines / total_expected if total_expected > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'matching_lines': matching_lines,
        'total_expected': total_expected,
        'total_actual': total_actual,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'exact_match': matching_lines == total_expected and total_expected == total_actual
    }

def show_diff_analysis(expected: str, actual_responses: list, test_results: list):
    """Display simple line-by-line comparison"""
    st.subheader("📊 Line Matching Results")
    
    # Simple results table
    table_rows = ["| Test # | Lines Matched | Total Expected |", 
                  "|--------|---------------|----------------|"]
    
    for i, result in enumerate(test_results, 1):
        table_rows.append(f"| {i} | {result['matching_lines']} | {result['total_expected']} |")
    
    # Add average row
    if test_results:
        avg_matched = sum(r['matching_lines'] for r in test_results) / len(test_results)
        avg_expected = sum(r['total_expected'] for r in test_results) / len(test_results)
        table_rows.append("|--------|---------------|----------------|")
        table_rows.append(f"| **Avg** | **{avg_matched:.1f}** | **{avg_expected:.1f}** |")
    
    st.markdown('\n'.join(table_rows))

st.title("🧪 Prompt Consistency Testing")

# Load available prompts
prompts_dir = Path("data/prompts")
if prompts_dir.exists():
    prompt_files = [f.stem for f in prompts_dir.glob("*.md")]
    selected_prompt = st.selectbox("Select Prompt Templ", prompt_files)
    
    # Test parameters
    col1, col2 = st.columns(2)
    with col1:
        num_requests = st.number_input("Number of AI Requests", min_value=1, max_value=50, value=10)
    with col2:
        test_dataset = st.selectbox("Test Dataset", ["example", "personal_productivity", "home_renovation"])
    
    # Live prompt preview
    if test_dataset:
        try:
            # Load dataset for preview
            dataset = dataset_manager.load_dataset(test_dataset)
            
            # Build prompt preview
            request = ClassificationRequest(
                dataset=dataset,
                prompt_variant=selected_prompt
            )
            current_prompt = classifier.prompt_builder.build_prompt(request)
            
            with st.expander("👁️ Live Prompt Preview", expanded=True):
                st.code(current_prompt.strip(), language="text")
                st.caption(f"Template: {selected_prompt} | Dataset: {test_dataset} | Characters: {len(current_prompt)}")
        except Exception as e:
            st.warning(f"Preview unavailable: {e}")
    
    # Expected results
    expected_results = st.text_area(
        "Expected Results (reference)", 
        height=200,
        placeholder="Paste expected classification results here..."
    )
    
    if st.button("🚀 Run Consistency Test", type="primary"):
        if expected_results.strip():
            with st.spinner(f"Running {num_requests} requests..."):
                try:
                    # Load dataset
                    dataset = dataset_manager.load_dataset(test_dataset)
                    
                    # Create run directory
                    run_dir = create_run_directory(selected_prompt)
                    
                    # Run multiple requests
                    actual_responses = []
                    similarities = []
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i in range(num_requests):
                        status_text.text(f"Processing request {i+1}/{num_requests}...")
                        progress_bar.progress((i + 1) / num_requests)
                        
                        # Create classification request
                        request = ClassificationRequest(
                            dataset=dataset,
                            prompt_variant=selected_prompt
                        )
                        
                        # Get AI response
                        response = classifier.classify(request)
                        raw_response = response.raw_response
                        actual_responses.append(raw_response)
                        
                        # Save individual response to run directory
                        saved_path = save_test_response(selected_prompt, raw_response, i + 1, run_dir)
                        
                        # Calculate similarity
                        similarity = calculate_similarity_score(expected_results, raw_response)
                        similarities.append(similarity)
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Store results for analysis
                    test_results = {
                        'similarities': similarities,
                        'responses': actual_responses,
                        'expected': expected_results,
                        'prompt': selected_prompt,
                        'dataset': test_dataset
                    }
                    
                    st.success(f"✅ Completed {num_requests} requests")
                    st.info(f"📁 Responses saved to: {run_dir}/")
                    
                    # Show saved files
                    with st.expander("📄 Saved Response Files", expanded=False):
                        result_files = sorted(run_dir.glob("result_*.txt"))
                        
                        for filepath in result_files:
                            st.code(f"{run_dir.name}/{filepath.name}", language="text")
                    
                    # Show comprehensive diff analysis
                    show_diff_analysis(expected_results, actual_responses, similarities)
                    
                except Exception as e:
                    st.error(f"Test failed: {str(e)}")
                    st.exception(e)
        else:
            st.error("Please provide expected results")
else:
    st.error("No prompts directory found")

# Add helpful tips
with st.expander("💡 Testing Tips", expanded=False):
    st.markdown("""
    **Best Practices:**
    - Use 10+ requests for reliable consistency measurement
    - Expected results should match your AI's typical output format
    - Similarity ≥80% indicates good consistency
    - Review responses with <60% similarity for prompt improvements
    
    **Interpreting Results:**
    - **Perfect consistency**: All responses identical (rare but ideal)
    - **High consistency**: 80%+ similarity across most responses
    - **Medium consistency**: 60-80% similarity (acceptable for most use cases)
    - **Low consistency**: <60% similarity (prompt needs refinement)
    """)