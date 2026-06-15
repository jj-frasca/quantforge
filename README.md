# QuantForge

AI-native quantitative research platform focused on **reproducibility, statistical
validation, and production-grade financial data engineering**. This is research
*infrastructure* — not a trading app, and it makes no claim to generate alpha. Its value
is methodological rigor: purged cross-validation, walk-forward analysis, the Probability
of Backtest Overfitting (PBO), and the Deflated Sharpe Ratio, after López de Prado (2018)
and Bailey et al.

> Full design rationale and every decision: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## What's shipped

End-to-end, all gates green (100% backend coverage; frontend ≥ 75%):

- **6 HTTP endpoints**: `GET /health`, `GET /api/v1/strategies` (catalog — single source
  of truth per ADR-010), `POST /api/v1/ingest`, `GET /api/v1/bars`, `POST /api/v1/backtest`,
  `POST /api/v1/validate` — cache-aside through the price-bar repository, sync `def` per
  ADR-009 so blocking yfinance + DB calls go through FastAPI's threadpool.
- **3 product pages**: **Data Explorer** (fetch + quality-gate + price chart), **Backtest
  Results** (per-strategy param form, equity curve with buy-and-hold overlay + trade-marker
  triangles, underwater drawdown, rolling Sharpe, daily-return distribution; customizable
  `initial_capital` + `cost_rate`), **Validation Report** (full statistical suite +
  plain-English verdicts per metric). Strategy dropdowns are catalog-driven and grouped
  by category (Trend / Mean Reversion / Breakout / Combination).
- **Data layer**: PriceBar / FundamentalData / quality models; yfinance adapter +
  OHLCV normalizer with split/dividend adjustment; 6-active-check DataQualityEngine
  (honest "flags potential X" wording — never "guarantees"); ingestion pipeline; **sync
  TimescaleDB repository on psycopg3** with Alembic migration (hypertable + index),
  Docker-gated integration tests.
- **Research engine**: vectorized pandas/numpy backtester (ADR-007 — vectorbt rejected:
  fails on Python 3.12); **11 strategies** in the catalog (SMA, Momentum, Mean Reversion
  z-score, RSI Mean Reversion, Donchian Breakout, Bollinger Bands, MACD, Vol-Targeted SMA,
  Keltner Channel, Trend-Filtered Mean Reversion, Triple MA Alignment) — each with the
  paper citation in `.claude/context/research-papers.md`; adding a strategy is a single
  backend diff (ADR-010); benchmark comparator; Monte Carlo simulator; experiment manifest.
- **Validation engine**: PBO via CSCV (Bailey 2015), Deflated Sharpe Ratio with
  multiple-testing penalty, walk-forward splits, purged K-fold CV with embargo, parameter
  stability, regime analysis. Every financial-math invariant (`docs/ARCHITECTURE.md` §8)
  is a Hypothesis property test.

The engine is calibrated to be honest: a random walk yields PBO ≈ 0.9 and does not pass.

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync, psycopg3),
  TimescaleDB, Alembic
- **Research**: NumPy, SciPy, Pandas — vectorized backtesting on pandas/numpy (ADR-007)
- **Frontend**: React 19 + TypeScript strict, Vite, Tanstack Query 5, Zustand 5,
  Recharts 3, Zod 4
- **Testing**: pytest + Hypothesis (backend); Vitest + React Testing Library + MSW
  (frontend); coverage gates 85% backend / 75% frontend, currently 100% / ~89%
- **Tooling**: uv (Python env), ruff (lint + format), mypy (strict), pre-commit, GitHub
  Actions CI (backend + frontend + pre-commit, gating every commit)

## Layout

```
backend/    FastAPI app, data layer, research engine, validation engine
frontend/   React dashboard (Vite + TS strict + Vitest)
docs/       ARCHITECTURE.md, ADRs (ADR-001..009), C4 diagrams
.claude/    Codified context: constitution (CLAUDE.md), domain agents,
            cold-memory docs, playbooks — drives AI-assisted sessions
```

## Getting started

```bash
# One-time
make dev              # start docker-compose (TimescaleDB + Redis + backend)
make migrate          # apply Alembic migrations

# Per-commit gates
make check            # backend: ruff + format-check + mypy + pytest + coverage
make frontend-check   # frontend: eslint + tsc + vitest + coverage
make check-all        # both, before pushing

# Run the UI locally
cd backend && uv run uvicorn app.main:app --reload   # one terminal
cd frontend && npm run dev                            # the other; Vite proxies /api
```

CI gates on deterministic synthetic fixtures only. Live-data tests (`@pytest.mark.live`)
and Docker-gated integration tests (`@pytest.mark.integration`) run locally via
`make test-live` / `make test-integration`.

## Why this is structured the way it is

- **Validation-first** (ADR-008): every Sharpe is deflated, every report carries its PBO,
  walk-forward, and parameter stability. A "good" Sharpe with PBO ≥ 0.5 fails.
- **Honest data quality** (CLAUDE.md rule 6): quality-check messages say "flags potential
  X" — never "prevents" or "guarantees." A gate informs review; it does not certify
  correctness.
- **Sync DB stack** (ADR-009): SQLAlchemy 2.0 sync on psycopg3, FastAPI routes are sync
  `def` and threadpooled by the framework. Researched and ratified 2026-05-28.
- **Cache-aside read path**: `/validate` and `/backtest` read bars from the repository
  first; on miss they run the ingestion pipeline (quality-gated) and re-read. TimescaleDB
  is the cache today; Redis is wired in config for a future hot path.
- **Codified context** (Vasilopoulos 2026 arXiv:2602.20478, validated across 283 dev
  sessions): three-tier — always-loaded constitution (`CLAUDE.md`), domain-expert agents
  (`.claude/agents/`), on-demand cold memory (`.claude/context/`). The repo is built to be
  picked up by a fresh Claude session and continued without losing rigor.

## Status

- **Phase 1** (foundation) — done
- **Phase 2** (data engineering) — done; TimescaleDB repo + Alembic migration built and
  integration-tested (`make test-integration`)
- **Phase 3** (research engine) — done; oracle tests pass on every invariant
- **Phase 4** (validation engine) — done; ValidationReport is the MVP deliverable
- **Phase 5** (product surface) — three pages shipped end-to-end (Data Explorer, Backtest
  Results, Validation); next: deploy + a Polygon adapter to enable vendor cross-validation
