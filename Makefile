.PHONY: help install dev down test test-live lint format migrate check coverage

# backend is a uv project living in ./backend
BE := cd backend && uv run
COV_MIN := 85

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Sync the backend virtualenv from pyproject/uv.lock
	cd backend && uv sync

dev: ## Start the docker-compose stack (TimescaleDB + Redis + backend)
	@test -f .env || cp .env.example .env
	docker compose up --build

down: ## Stop the docker-compose stack
	docker compose down

test: ## Run tests with coverage — excludes live + integration (DB) tests
	$(BE) pytest -m "not live and not integration" --cov=app --cov-report=term-missing --cov-fail-under=$(COV_MIN)

test-live: ## Run live-data tests (yfinance). Local only — never in CI.
	$(BE) pytest -m live

test-integration: ## Run DB-backed integration tests (needs Docker). Local only — not in CI.
	$(BE) pytest -m integration

coverage: ## Coverage report (synthetic only), HTML + terminal
	$(BE) pytest -m "not live" --cov=app --cov-report=term-missing --cov-report=html

lint: ## ruff lint + format check + mypy (eslint added in Phase 5)
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app

format: ## Auto-format with ruff
	cd backend && uv run ruff format . && uv run ruff check --fix .

migrate: ## Run alembic migrations (Phase 2+)
	$(BE) alembic upgrade head

check: lint test ## Lint + tests + coverage gate — run before every commit
