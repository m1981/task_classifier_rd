import streamlit as st
import os
from pathlib import Path
import difflib
from services import TaskClassifier, PromptBuilder, ResponseParser, DatasetManager
from models import ClassificationRequest
import anthropic

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
    lines = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            lines.append(line)
    return '\n'.join(lines)

def calculate_similarity_score(expected: str, actual: str) -> float:
    """Calculate similarity score between expected and actual results"""
    expected_norm = normalize_response_text(expected)
    actual_norm = normalize_response_text(actual)
    
    matcher = difflib.SequenceMatcher(None, expected_norm, actual_norm)
    return matcher.ratio()

def show_diff_analysis(expected: str, actual_responses: list, test_results: dict):
    """Display comprehensive diff analysis"""
    st.subheader("📊 Consistency Analysis")
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_similarity = sum(test_results['similarities']) / len(test_results['similarities'])
        st.metric("Avg Similarity", f"{avg_similarity:.1%}")
    with col2:
        st.metric("Best Match", f"{max(test_results['similarities']):.1%}")
    with col3:
        st.metric("Worst Match", f"{min(test_results['similarities']):.1%}")
    with col4:
        high_consistency = sum(1 for s in test_results['similarities'] if s >= 0.8)
        st.metric("High Consistency", f"{high_consistency}/{len(actual_responses)}")
    
    # Detailed results table
    st.subheader("📋 Individual Test Results")
    
    table_rows = ["| Test # | Similarity | Status | Preview |", 
                  "|--------|------------|--------|---------|"]
    
    for i, (response, similarity) in enumerate(zip(actual_responses, test_results['similarities']), 1):
        status = "✅ Good" if similarity >= 0.8 else "⚠️ Medium" if similarity >= 0.6 else "❌ Poor"
        preview = response[:50].replace('\n', ' ') + "..." if len(response) > 50 else response.replace('\n', ' ')
        table_rows.append(f"| {i} | {similarity:.1%} | {status} | {preview} |")
    
    st.markdown('\n'.join(table_rows))
    
    # Show detailed diff for problematic responses
    poor_responses = [(i, resp, sim) for i, (resp, sim) in enumerate(zip(actual_responses, test_results['similarities'])) if sim < 0.8]
    
    if poor_responses:
        with st.expander(f"🔍 Detailed Diff Analysis ({len(poor_responses)} responses need review)", expanded=False):
            for i, response, similarity in poor_responses:
                st.write(f"**Test #{i+1} - Similarity: {similarity:.1%}**")
                
                # Generate unified diff
                expected_lines = normalize_response_text(expected).splitlines(keepends=True)
                actual_lines = normalize_response_text(response).splitlines(keepends=True)
                
                diff = list(difflib.unified_diff(
                    expected_lines, 
                    actual_lines,
                    fromfile='Expected',
                    tofile=f'Actual #{i+1}',
                    lineterm=''
                ))
                
                if diff:
                    diff_text = ''.join(diff)
                    st.code(diff_text, language="diff")
                else:
                    st.info("No significant differences found")
                st.write("---")
    
    # Response variance analysis
    st.subheader("🔄 Response Variance")
    if len(actual_responses) > 1:
        # Find most common response patterns
        response_counts = {}
        for response in actual_responses:
            normalized = normalize_response_text(response)
            response_counts[normalized] = response_counts.get(normalized, 0) + 1
        
        if len(response_counts) == 1:
            st.success("🎯 Perfect consistency - All responses identical!")
        else:
            st.write(f"Found {len(response_counts)} unique response patterns:")
            for pattern, count in sorted(response_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(actual_responses)) * 100
                st.write(f"- **{count}/{len(actual_responses)} responses ({percentage:.1f}%)**: {pattern[:100]}...")

st.title("🧪 Prompt Consistency Testing")

# Load available prompts
prompts_dir = Path("data/prompts")
if prompts_dir.exists():
    prompt_files = [f.stem for f in prompts_dir.glob("*.md")]
    selected_prompt = st.selectbox("Select Prompt Template", prompt_files)
    
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
                    
                    # Show comprehensive diff analysis
                    show_diff_analysis(expected_results, actual_responses, test_results)
                    
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