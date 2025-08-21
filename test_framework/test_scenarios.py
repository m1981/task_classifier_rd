from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
import json
from datetime import datetime
from models import DatasetContent, ClassificationRequest

@dataclass
class TestScenario:
    name: str
    dataset: DatasetContent
    inbox_tasks: List[str]
    expected_response: str
    description: str
    tags: List[str]

class ConsistencyTestRunner:
    def __init__(self, classifier, dataset_manager):
        self.classifier = classifier
        self.dataset_manager = dataset_manager
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def run_matrix_test(self, prompts: List[str], scenarios: List[str], runs_per_combo: int = 10):
        """Test all prompt x scenario combinations"""
        results = {}
        
        # Create timestamped run directory
        timestamp = datetime.now().strftime("%m-%d_%H%M%S")
        run_dir = self.results_dir / f"matrix_test_{timestamp}"
        run_dir.mkdir(exist_ok=True)
        
        print(f"📁 Saving debug output to: {run_dir}")
        
        for prompt in prompts:
            for scenario in scenarios:
                key = f"{prompt}_vs_{scenario}"
                print(f"🧪 Testing {key}...")
                results[key] = self._run_scenario_test(prompt, scenario, runs_per_combo, run_dir)
        
        # Save summary report
        report = self._generate_matrix_report(results)
        with open(run_dir / "summary.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _run_scenario_test(self, prompt: str, scenario: str, runs: int, run_dir: Path):
        """Run multiple tests for one prompt + scenario combination"""
        dataset = self.dataset_manager.load_dataset(scenario)
        responses = []
        
        # Create subdirectory for this test combo
        test_dir = run_dir / f"{prompt}_vs_{scenario}"
        test_dir.mkdir(exist_ok=True)
        
        for i in range(runs):
            request = ClassificationRequest(dataset=dataset, prompt_variant=prompt)
            response = self.classifier.classify(request)
            
            # Save individual response files
            with open(test_dir / f"run_{i+1:02d}_prompt.txt", 'w') as f:
                f.write(response.prompt_used)
            
            with open(test_dir / f"run_{i+1:02d}_response.txt", 'w') as f:
                f.write(response.raw_response)
            
            with open(test_dir / f"run_{i+1:02d}_parsed.json", 'w') as f:
                parsed_data = {
                    'num_results': len(response.results),
                    'results': [
                        {
                            'task': r.task,
                            'project': r.suggested_project,
                            'confidence': r.confidence
                        } for r in response.results
                    ]
                }
                json.dump(parsed_data, f, indent=2)
            
            responses.append(response.raw_response)
            
            # Debug: Show first few lines of response
            if i == 0:
                print(f"🔍 DEBUG: First response preview for {prompt}_vs_{scenario}:")
                lines = response.raw_response.split('\n')[:5]
                for line in lines:
                    print(f"    {repr(line)}")
                print(f"    ... (total {len(response.raw_response)} chars)")
        
        return {
            'responses': responses,
            'consistency_score': self._calculate_consistency(responses),
            'runs': runs,
            'test_dir': str(test_dir)
        }
    
    def _calculate_consistency(self, responses):
        """Calculate consistency score"""
        if not responses:
            return 0.0
        unique_responses = len(set(responses))
        total_responses = len(responses)
        return 1.0 - (unique_responses - 1) / max(total_responses - 1, 1)
    
    def _generate_matrix_report(self, results):
        """Generate summary report"""
        report = {
            'summary': {},
            'details': results,
            'recommendations': []
        }
        
        for key, result in results.items():
            score = result['consistency_score']
            report['summary'][key] = {
                'consistency': f"{score:.2%}",
                'status': 'Good' if score >= 0.8 else 'Poor' if score < 0.6 else 'Fair',
                'test_dir': result.get('test_dir', '')
            }
            
            if score < 0.6:
                report['recommendations'].append(f"Review {key} - low consistency ({score:.2%}) - check {result.get('test_dir', '')}")
        
        return report

def load_test_scenarios():
    """Load available test scenarios"""
    # For now, return available datasets as scenarios
    from services import DatasetManager
    dm = DatasetManager()
    return dm.list_datasets()

def load_prompts():
    """Load available prompt variants"""
    return ["basic", "diy_renovation"]  # Add your prompt variants
