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
.PHONY: install
install: ## Install dependencies via uv
	uv sync

.PHONY: run
run: ## Run the Streamlit application
	uv run streamlit run app.py

.PHONY: test-html
test-html: ## Run tests with HTML coverage report
	uv run pytest --cov=services --cov=models --cov=pages --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(RESET)"

.PHONY: coverage
coverage: ## Generate coverage report and open in browser
	uv run pytest --cov=services --cov=models --cov=pages --cov-report=html
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "$(YELLOW)Open htmlcov/index.html in your browser$(RESET)"; \
	fi

.PHONY: test
test: ## Run tests with coverage
	uv run pytest --cov=services --cov=models --cov=pages --cov-report=term-missing

.PHONY: clean
clean: ## Remove cache and virtual environment
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
