# QuantForge

AI-native quantitative research and experimentation platform focused on
**reproducibility, statistical validation, and production-grade financial data
engineering**. This is research *infrastructure* — not a trading app, and it makes
no claim to generate alpha. Its value is methodological rigor: purged
cross-validation, walk-forward analysis, the Probability of Backtest Overfitting
(PBO), and the Deflated Sharpe Ratio, after López de Prado (2018) and Bailey et al.

> Full design rationale and every decision: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), TimescaleDB, Redis
- **Research**: NumPy/SciPy, Pandas/Polars, statsmodels, scikit-learn, vectorbt
- **Frontend** (Phase 5): React 18 + TypeScript, Vite, Tanstack Query, Recharts, Tailwind
- **Tooling**: uv (env + deps), ruff + black, mypy (strict), pytest + Hypothesis

## Layout

```
backend/     FastAPI app, data layer, research engine, validation engine
frontend/    React dashboard (Phase 5+)
docs/        ARCHITECTURE.md, ADRs, C4 diagrams
.claude/     Codified context: constitution, domain agents, cold-memory docs, playbooks
```

## Getting started

```bash
make dev      # start docker-compose (TimescaleDB + Redis + backend)
make check    # lint + test + coverage — run before every commit
make test     # tests with coverage (synthetic fixtures only)
make test-live # live-data tests (yfinance); local only, excluded from CI
```

## Status

**Phase 1 — Foundation** (in progress). Build phases are tracked in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §9. The MVP milestone is a real
`ValidationReport` produced end-to-end (Phases 1–4 + a minimal frontend).
