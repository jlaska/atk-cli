.DEFAULT_GOAL := help

.PHONY: help lint lint-fix setup install-hooks clean

help: ## Print available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

lint: ## Run all pre-commit hooks against all files
	uvx pre-commit run --all-files

lint-fix: ## Auto-fix issues then run pre-commit
	uvx pre-commit run --all-files ruff --hook-stage manual || true
	uvx pre-commit run --all-files

setup: install-hooks ## Alias for install-hooks

install-hooks: ## Install pre-commit git hooks
	uvx pre-commit install

clean: ## Remove Python cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .ruff_cache dist build *.egg-info
