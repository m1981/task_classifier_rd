# Colors for help system
BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Usage:$(RESET)\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development
.PHONY: run
run: ## Start Streamlit app
	streamlit run app.py

.PHONY: test-ui
test-ui: ## Open consistency testing UI
	streamlit run pages/consistency_test.py

##@ Testing
.PHONY: generate-baselines
generate-baselines: ## Generate baseline responses for regression testing
	python test_framework/automated_testing.py

.PHONY: test-matrix
test-matrix: ## Run matrix test (all prompts vs all datasets)
	PYTHONPATH=. python pages/consistency_test.py cli

.PHONY: detect-regressions
detect-regressions: ## Check for performance regressions against baselines
	PYTHONPATH=. python -c "from test_framework.automated_testing import detect_regressions; detect_regressions()"

.PHONY: test-consistency
test-consistency: ## Run consistency test for specific prompt+dataset (PROMPT=basic DATASET=example)
	PYTHONPATH=. python -c "from test_framework.automated_testing import run_consistency_test; print(f'Consistency: {run_consistency_test(\"$(PROMPT)\", \"$(DATASET)\"):.2%}')"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	PYTHONPATH=. pytest --cov=services --cov=models --cov=dataset_io --cov-report=term-missing -v

.PHONY: test-coverage-html
test-coverage-html: ## Generate HTML coverage report
	PYTHONPATH=. pytest --cov=services --cov=models --cov=dataset_io --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/index.html"

##@ Data Management
.PHONY: list-datasets
list-datasets: ## List available datasets
	PYTHONPATH=. python -c "from services import DatasetManager; dm = DatasetManager(); print('Available datasets:'); [print(f'  - {d}') for d in dm.list_datasets()]"

.PHONY: list-prompts
list-prompts: ## List available prompt templates
	python -c "from pathlib import Path; prompts = [f.stem for f in Path('data/prompts').glob('*.md')]; print('Available prompts:'); [print(f'  - {p}') for p in prompts]"

##@ Cleanup
.PHONY: clean-results
clean-results: ## Remove all test results
	rm -rf test_results/*
	rm -rf test_data/baselines/*

.PHONY: clean-cache
clean-cache: ## Clear Streamlit cache
	rm -rf .streamlit/cache

##@ Examples
.PHONY: example-full-test
example-full-test: ## Run complete testing workflow
	@echo "$(GREEN)Step 1: Generating baselines...$(RESET)"
	make generate-baselines
	@echo "$(GREEN)Step 2: Running matrix test...$(RESET)"
	make test-matrix
	@echo "$(GREEN)Step 3: Checking regressions...$(RESET)"
	make detect-regressions

.PHONY: example-quick-test
example-quick-test: ## Quick consistency test (basic prompt + example dataset)
	make test-consistency PROMPT=basic DATASET=example