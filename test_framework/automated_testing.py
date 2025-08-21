import json
from pathlib import Path
from collections import Counter
from services import TaskClassifier, PromptBuilder, ResponseParser, DatasetManager
from models import ClassificationRequest
import anthropic

REGRESSION_THRESHOLD = 0.1
test_data_dir = Path("test_data")
baselines_dir = test_data_dir / "baselines"
baselines_dir.mkdir(parents=True, exist_ok=True)

# Initialize services
client = anthropic.Anthropic()
classifier = TaskClassifier(client, PromptBuilder(), ResponseParser())
dataset_manager = DatasetManager()

def find_consensus_response(responses):
    """Find most common response from multiple runs"""
    response_counts = Counter(responses)
    return response_counts.most_common(1)[0][0]

def save_baseline(prompt: str, scenario: str, baseline: str):
    """Save baseline response to file"""
    baseline_file = baselines_dir / f"{prompt}_{scenario}_baseline.txt"
    with open(baseline_file, 'w') as f:
        f.write(baseline)

def load_baseline(prompt: str, scenario: str) -> str:
    """Load baseline response"""
    baseline_file = baselines_dir / f"{prompt}_{scenario}_baseline.txt"
    if baseline_file.exists():
        return baseline_file.read_text()
    return ""

def calculate_consistency_score(responses):
    """Calculate consistency score from multiple responses"""
    if not responses:
        return 0.0
    
    # Count unique responses
    unique_responses = len(set(responses))
    total_responses = len(responses)
    
    # Higher consistency = fewer unique responses
    return 1.0 - (unique_responses - 1) / max(total_responses - 1, 1)

def run_consistency_test(prompt: str, scenario_name: str, runs: int = 10):
    """Run consistency test for prompt + scenario"""
    dataset = dataset_manager.load_dataset(scenario_name)
    responses = []
    
    for _ in range(runs):
        request = ClassificationRequest(dataset=dataset, prompt_variant=prompt)
        response = classifier.classify(request)
        responses.append(response.raw_response)
    
    return calculate_consistency_score(responses)

def load_baseline_score(prompt: str, scenario: str) -> float:
    """Load baseline consistency score"""
    score_file = baselines_dir / f"{prompt}_{scenario}_score.json"
    if score_file.exists():
        with open(score_file, 'r') as f:
            data = json.load(f)
            return data.get('consistency_score', 0.0)
    return 0.0

def alert_regression(prompt: str, scenario: str, current: float, baseline: float):
    """Alert about regression"""
    print(f"🚨 REGRESSION DETECTED:")
    print(f"   Prompt: {prompt}")
    print(f"   Scenario: {scenario}")
    print(f"   Current: {current:.2%}")
    print(f"   Baseline: {baseline:.2%}")
    print(f"   Drop: {baseline - current:.2%}")

def generate_baseline(prompt: str, scenario: str, runs: int = 20):
    """Generate golden response from multiple runs"""
    responses = []
    for _ in range(runs):
        dataset = dataset_manager.load_dataset(scenario)
        request = ClassificationRequest(dataset=dataset, prompt_variant=prompt)
        response = classifier.classify(request)
        responses.append(response.raw_response)
    
    # Use most common response as baseline
    baseline = find_consensus_response(responses)
    save_baseline(prompt, scenario, baseline)
    
    # Save consistency score
    score = calculate_consistency_score(responses)
    score_file = baselines_dir / f"{prompt}_{scenario}_score.json"
    with open(score_file, 'w') as f:
        json.dump({'consistency_score': score, 'runs': runs}, f)
    
    print(f"✅ Generated baseline for {prompt} + {scenario} (score: {score:.2%})")

def detect_regressions():
    """Compare current performance against stored baselines"""
    available_datasets = dataset_manager.list_datasets()
    available_prompts = ["basic", "diy_renovation"]  # Add your prompt variants
    
    for scenario in available_datasets:
        for prompt in available_prompts:
            try:
                current_score = run_consistency_test(prompt, scenario)
                baseline_score = load_baseline_score(prompt, scenario)
                
                if baseline_score > 0 and current_score < baseline_score - REGRESSION_THRESHOLD:
                    alert_regression(prompt, scenario, current_score, baseline_score)
                else:
                    print(f"✅ {prompt} + {scenario}: {current_score:.2%} (baseline: {baseline_score:.2%})")
            except Exception as e:
                print(f"❌ Failed to test {prompt} + {scenario}: {e}")

if __name__ == "__main__":
    print("🧪 Running automated testing...")
    
    # Generate baselines if they don't exist
    print("\n📊 Generating baselines...")
    generate_baseline("basic", "example", runs=10)
    
    # Run regression detection
    print("\n🔍 Detecting regressions...")
    detect_regressions()