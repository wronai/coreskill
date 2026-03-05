# evo-engine Testing Makefile
# Fully automated Docker-based testing

.PHONY: help test test-unit test-integration test-smoke test-e2e clean build report \
       up down web desktop logs status pull-model clean-chat

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m

help: ## Show this help message
	@echo -e "$(BLUE)evo-engine Docker Test Suite$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make test              # Run all tests"
	@echo "  make test-unit         # Run unit tests only (fast)"
	@echo "  make test-integration  # Run integration tests"
	@echo "  make clean test        # Clean and run all tests"

test: ## Run all tests in Docker
	@echo -e "$(BLUE)[TEST]$(NC) Running complete test suite..."
	@./scripts/run_tests.sh all

test-unit: ## Run unit tests only (fast)
	@echo -e "$(BLUE)[TEST]$(NC) Running unit tests..."
	@./scripts/run_tests.sh unit

test-integration: ## Run integration tests
	@echo -e "$(BLUE)[TEST]$(NC) Running integration tests..."
	@./scripts/run_tests.sh integration

test-smoke: ## Quick smoke test
	@echo -e "$(BLUE)[TEST]$(NC) Running smoke tests..."
	@./scripts/run_tests.sh smoke

test-e2e: ## Run E2E tests only
	@echo -e "$(BLUE)[TEST]$(NC) Running E2E tests..."
	@./scripts/run_tests.sh e2e

test-verbose: ## Run all tests with verbose output
	@echo -e "$(BLUE)[TEST]$(NC) Running tests with verbose output..."
	@./scripts/run_tests.sh -v all

test-rebuild: ## Rebuild images and run all tests
	@echo -e "$(BLUE)[TEST]$(NC) Rebuilding and running tests..."
	@./scripts/run_tests.sh -r all

clean: ## Clean test artifacts and Docker containers
	@echo -e "$(YELLOW)[CLEAN]$(NC) Cleaning up..."
	@docker-compose -f docker-compose.test.yml rm -f 2>/dev/null || true
	@rm -rf test-results/ coverage/ htmlcov/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo -e "$(GREEN)[CLEAN]$(NC) Done"

clean-all: ## Deep clean including Docker images
	@echo -e "$(YELLOW)[CLEAN]$(NC) Deep cleaning..."
	@make clean
	@docker rmi evo-engine-test evo-engine-test-unit evo-engine-test-integration 2>/dev/null || true
	@echo -e "$(GREEN)[CLEAN]$(NC) Images removed"

build: ## Build test Docker images
	@echo -e "$(BLUE)[BUILD]$(NC) Building test images..."
	@docker-compose -f docker-compose.test.yml build

shell: ## Open shell in test container
	@echo -e "$(BLUE)[SHELL]$(NC) Opening test container shell..."
	@docker-compose -f docker-compose.test.yml run --rm test bash

report: ## Show test report from previous run
	@echo -e "$(BLUE)[REPORT]$(NC) Test Results"
	@echo "===================="
	@if [ -f test-results/junit.xml ]; then \
		total=$$(grep -o 'tests="[0-9]*"' test-results/junit.xml | head -1 | sed 's/[^0-9]//g'); \
		failures=$$(grep -o 'failures="[0-9]*"' test-results/junit.xml | head -1 | sed 's/[^0-9]//g' || echo "0"); \
		errors=$$(grep -o 'errors="[0-9]*"' test-results/junit.xml | head -1 | sed 's/[^0-9]//g' || echo "0"); \
		echo -e "Total:    $(CYAN)$${total:-0}$(NC)"; \
		echo -e "Failures: $(RED)$${failures:-0}$(NC)"; \
		echo -e "Errors:   $(RED)$${errors:-0}$(NC)"; \
		passed=$$((total - failures - errors)); \
		echo -e "Passed:   $(GREEN)$${passed:-0}$(NC)"; \
	fi
	@echo ""
	@if [ -f coverage/coverage.xml ]; then \
		line_rate=$$(grep -o 'line-rate="[0-9.]*"' coverage/coverage.xml | head -1 | sed 's/[^0-9.]//g'); \
		coverage=$$(python3 -c "print(f'$${line_rate} * 100:.1f')" 2>/dev/null || echo "?"); \
		echo -e "Coverage: $(CYAN)$${coverage}%$(NC)"; \
	fi
	@echo ""
	@echo "Reports:"
	@echo "  HTML:  test-results/report.html"
	@echo "  JUnit: test-results/junit.xml"

# CI/CD targets for GitHub Actions / GitLab CI
ci-test: ## Run tests for CI (JUnit output)
	@echo -e "$(BLUE)[CI]$(NC) Running CI tests..."
	@docker-compose -f docker-compose.test.yml run --rm test python -m pytest tests/ \
		-v --tb=short --timeout=60 \
		--junitxml=/app/test-results/junit.xml \
		--cov=cores --cov-report=xml:/app/coverage/coverage.xml

ci-smoke: ## Quick smoke test for CI
	@echo -e "$(BLUE)[CI]$(NC) Running smoke test..."
	@docker-compose -f docker-compose.test.yml run --rm test-smoke

# ============================================================================
# Chat UI — CoreSkill Demo (Docker Compose)
# ============================================================================
CHAT_COMPOSE := docker compose -f docker-compose.chat.yml

up: ## Start all chat UI services (backend + frontend + ollama)
	@echo -e "$(BLUE)[CHAT]$(NC) Starting CoreSkill Demo..."
	@$(CHAT_COMPOSE) down --remove-orphans 2>/dev/null || true
	@$(CHAT_COMPOSE) up -d --build --force-recreate
	@echo -e "$(GREEN)[CHAT]$(NC) Ready at http://localhost:3000"

down: ## Stop all chat UI services
	@echo -e "$(YELLOW)[CHAT]$(NC) Stopping..."
	@$(CHAT_COMPOSE) down --remove-orphans
	@echo -e "$(GREEN)[CHAT]$(NC) Stopped"

web: up ## Start + open in browser
	@echo -e "$(BLUE)[CHAT]$(NC) Opening browser..."
	@sleep 2
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000"

desktop: up ## Start + open as desktop app (Chrome --app or Electron)
	@echo -e "$(BLUE)[CHAT]$(NC) Launching desktop app..."
	@./desktop/run.sh

logs: ## Show live logs from chat services
	@$(CHAT_COMPOSE) logs -f --tail=50

logs-chat: ## Show chat history from backend
	@docker exec coreskill-api cat /app/data/chat_history.jsonl 2>/dev/null | tail -20 || echo "No chat history yet"

diagnose: ## Run LLM connectivity diagnostics
	@echo -e "$(BLUE)[CHAT]$(NC) Running diagnostics..."
	@curl -s http://localhost:8001/api/diagnose 2>/dev/null | python3 -m json.tool || echo -e "$(RED)Diagnostics failed$(NC)"

status: ## Show status of chat services + API health
	@echo -e "$(BLUE)[CHAT]$(NC) Service status:"
	@$(CHAT_COMPOSE) ps
	@echo ""
	@echo -e "$(BLUE)[CHAT]$(NC) API health:"
	@curl -sf http://localhost:8001/health 2>/dev/null && echo "" || echo -e "$(RED)API not reachable$(NC)"
	@echo -e "$(BLUE)[CHAT]$(NC) LLM status:"
	@curl -sf http://localhost:8001/api/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo -e "$(YELLOW)API not responding$(NC)"

pull-model: ## Manually pull Ollama model
	@echo -e "$(BLUE)[CHAT]$(NC) Pulling qwen2.5:1.5b..."
	@docker exec coreskill-ollama ollama pull qwen2.5:1.5b

clean-chat: down ## Remove chat containers and volumes
	@echo -e "$(YELLOW)[CHAT]$(NC) Cleaning chat data..."
	@$(CHAT_COMPOSE) down -v
	@echo -e "$(GREEN)[CHAT]$(NC) Clean"
