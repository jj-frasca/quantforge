.PHONY: help install dev down test test-live test-integration lint format migrate check coverage \
        frontend-install frontend-lint frontend-test frontend-check e2e e2e-install check-all

# backend is a uv project living in ./backend
BE := cd backend && uv run
FE := cd frontend &&
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

lint: ## Backend lint: ruff lint + format check + mypy
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app

format: ## Auto-format with ruff
	cd backend && uv run ruff format . && uv run ruff check --fix .

migrate: ## Run alembic migrations (Phase 2+)
	$(BE) alembic upgrade head

check: lint test ## Backend gate: lint + tests + coverage — run before every backend commit

# --- frontend (React/TS, ./frontend) ---
frontend-install: ## Install frontend deps from package-lock (npm ci)
	$(FE) npm ci

frontend-lint: ## Frontend eslint + tsc typecheck
	$(FE) npm run lint && npm run typecheck

frontend-test: ## Frontend tests with coverage gate (>=75%)
	$(FE) npm run coverage

frontend-check: frontend-lint frontend-test ## Frontend gate: lint + typecheck + tests

e2e-install: ## One-time: install the Playwright Chromium browser
	$(FE) npx playwright install chromium

e2e: ## Browser e2e smoke (real backend + dev server) — local only, NOT a CI/coverage gate
	$(FE) npm run e2e

check-all: check frontend-check ## Full gate: backend + frontend
