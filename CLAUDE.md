# QuantForge — Claude Code Constitution

## What This Is
AI-native quantitative research platform. Research rigor and data engineering
quality are the primary goals. See docs/ARCHITECTURE.md for full context.

## Non-Negotiable Rules
1. Tests FIRST. Test must fail before implementation. No exceptions.
2. One logical unit per commit. Tests and implementation in same commit.
3. Commit body follows docs/adr/COMMIT_TEMPLATE.md exactly.
4. Write ADR before implementing any non-trivial architecture decision.
5. Coverage must not drop: backend ≥ 85%, frontend ≥ 75%.
6. DataQualityEngine checks flag POTENTIAL issues — never claim to prevent them.
7. Paper trading is IN scope for forward-testing (ADR-019 — paper only, NO real-money orders).
   WebSockets and order-book/HFT microstructure remain out of scope (ADR-001).
8. Never hardcode secrets. All config via app/config.py (Pydantic Settings).
9. Primary data source is yfinance (no API key). Polygon is the second vendor (Phase 3+).

## Commands
make dev          → start docker-compose environment (TimescaleDB + Redis + backend)
make test         → tests with coverage; excludes -m live and -m integration (DB)
make test-live    → live-data tests (pytest -m live); local only, never in CI
make test-integration → DB-backed tests (pytest -m integration); needs Docker, not in CI
make lint         → backend ruff + format-check + mypy
make migrate      → run alembic migrations
make check        → backend gate: lint + test + coverage (run before every backend commit)
make frontend-check → frontend gate: eslint + tsc + vitest coverage (>=75%); run before frontend commits
make check-all    → backend + frontend gates together

## Architecture (one paragraph)
FastAPI backend (Python 3.12) in /backend. React 19 + TypeScript in /frontend (Vite + Vitest).
TimescaleDB (PostgreSQL) + Redis. SYNCHRONOUS stack: SQLAlchemy 2.0 sync on the psycopg
(psycopg3) driver; FastAPI DB routes are sync `def` (threadpooled) — see ADR-009. Backtesting
is vectorized pandas/numpy, NOT vectorbt — see ADR-007. All data flows: DataSourceAdapter →
canonical schema → DataQualityEngine before any research or validation component uses it.
Monte Carlo lives in research/simulation/. BenchmarkComparator in research/benchmarks/.
Full diagram: docs/diagrams/c4-context.md.

## Testing & CI Gate
CI gates on deterministic synthetic fixtures ONLY. Live-data tests (e.g. live yfinance)
are marked @pytest.mark.live, run via `make test-live` locally, and are EXCLUDED from CI.
Financial-math invariants must be Hypothesis property tests (see ARCHITECTURE.md §8).

## Agent Routing
Working on data ingestion, schemas, normalization, quality, storage
  → invoke data-engineer agent
  → read .claude/context/data-contracts.md for schemas and SQL

Working on strategies, backtesting, portfolio, metrics, benchmarks, experiments
  → invoke research-expert agent
  → read .claude/context/backtesting-spec.md

Working on PBO, walk-forward, purged CV, deflated Sharpe, regime analysis
  → invoke research-expert agent
  → read .claude/context/validation-methodology.md
  → read .claude/context/research-papers.md

Working on FastAPI endpoints, response schemas, API versioning
  → read .claude/context/api-contracts.md

Working on the frontend (React/TS dashboard, components, charts, frontend tests)
  → invoke frontend-engineer agent
  → read .claude/context/api-contracts.md

Commit ready             → use commit-writer skill
New function/class       → use tdd-cycle skill
New architecture choice  → use the ADR template (adr-creator skill is deferred)

## Cold Memory Index
.claude/context/INDEX.md              → find the right doc for any task
.claude/context/data-contracts.md     → schemas, SQL, mandatory query filters
.claude/context/validation-methodology.md → PBO, purged CV, DSR implementation
.claude/context/backtesting-spec.md   → engine, portfolio, metrics, experiment manifest
.claude/context/research-papers.md    → citations with implementation summaries
.claude/context/api-contracts.md      → full endpoint specifications

## Hard Constraints
- Never write production code without a test
- Never write a vague commit message
- DB access is sync (psycopg3, ADR-009); use sync `def` routes for DB work — never call a blocking driver inside an `async def`
- Never skip type annotations (mypy strict enforced in CI)
- Never start a new phase until the current phase is fully passing and committed
- Never put module-specific content in this file — it belongs in agents or context docs
