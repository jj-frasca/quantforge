# QuantForge

AI-native quantitative research and experimentation platform focused on
**reproducibility, statistical validation, and production-grade financial data
engineering**. This is research *infrastructure* — not a trading app, and it makes
no claim to generate alpha. Its value is methodological rigor: purged
cross-validation, walk-forward analysis, the Probability of Backtest Overfitting
(PBO), and the Deflated Sharpe Ratio, after López de Prado (2018) and Bailey et al.

> Full design rationale and every decision: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, TimescaleDB, Redis
- **Research**: NumPy, SciPy, Pandas — vectorized backtesting on pandas/numpy (ADR-007;
  vectorbt was evaluated and rejected — it fails to build on Python 3.12)
- **Frontend** (Phase 5): React 18 + TypeScript, Vite, Tanstack Query, Recharts, Tailwind
- **Tooling**: uv (env + deps), ruff (lint + format), mypy (strict), pytest + Hypothesis

## Layout

```
backend/     FastAPI app, data layer, research engine, validation engine
frontend/    React dashboard (Phase 5+)
docs/        ARCHITECTURE.md, ADRs, C4 diagrams
.claude/     Codified context: constitution, domain agents, cold-memory docs, playbooks
```

## Getting started

```bash
make dev              # start docker-compose (TimescaleDB + Redis + backend)
make check            # lint (ruff + format + mypy) + tests + coverage — run before every commit
make test             # tests with coverage; excludes -m live and -m integration
make test-live        # live-data tests (yfinance); local only, excluded from CI
make test-integration # DB-backed tests; needs Docker, excluded from CI
```

## Status

The validation-first backend (Phases 1–4) is complete and the **MVP milestone** is met: a real
`ValidationReport` is produced end-to-end — ingest → quality-gate → backtest (with costs +
benchmark) → PBO / Deflated Sharpe / walk-forward / purged CV / parameter stability. The engine
is calibrated to be honest (a random walk yields PBO ≈ 0.9 and does not pass). Build phases are
tracked in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §9.

- **Phase 1 — Foundation**: done.
- **Phase 2 — Data engineering**: done (models, yfinance adapter + normalizer, 8-check quality
  engine, ingestion pipeline, ORM schema). TimescaleDB repository + Alembic migration are
  Docker-gated and pending ADR-009 ratification.
- **Phase 3 — Research engine**: done (vectorized backtester + oracle tests, 3 strategies,
  benchmark comparator, Monte Carlo, experiment manifest).
- **Phase 4 — Validation engine**: done (PBO via CSCV, Deflated Sharpe, walk-forward, purged
  CV, parameter stability, regime analysis, `ValidationEngine` → `ValidationReport`).
- **Phase 5 — Frontend**: not started; the `ValidationReport` page is the priority.

Every financial-math invariant (ARCHITECTURE.md §8) is enforced by a Hypothesis property test;
backend coverage is at 100%.
