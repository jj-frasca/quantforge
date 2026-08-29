# QuantForge

AI-native quantitative research platform focused on **reproducibility, statistical
validation, and production-grade financial data engineering**. This is research
*infrastructure* — not a trading app, and it makes no claim to generate alpha. Its value
is methodological rigor: purged cross-validation, walk-forward analysis, the Probability
of Backtest Overfitting (PBO), and a multiple-testing-adjusted Sharpe margin adapted from
Bailey and López de Prado (2014). FINDING-007 records why that margin is not the paper's
statistic; ADR-054 implements the paper's probability form beside it and corrects every surface
that called the margin by the paper's name.

> Full design rationale and every decision: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## What has been measured

Most backtesting projects report the strategies they found. This one reports **what its own gate
does**, because a graduation criterion whose error rates are unknown cannot support any claim made
with it. Every number below is produced by a committed workflow and can be re-run.

| question | answer | how |
|---|---|---|
| **Type-I error** — how often does the whole pipeline graduate a symbol with *no edge by construction*? | **0/200** under both iid-normal and bootstrap nulls, with ADR-050's dispersion and judged at the hunt's own 5400-bar history. Max DSR -0.415 (iid) / -0.269 (bootstrap) | `null-calibration.yml` (ADR-036/037/050/051) |
| Do those false graduates survive the universe-deflation bar? | **0 of 200**, in both nulls | same run |
| **Power** — does the gate detect a *planted* edge at production parity? | **Yes, and it is measured: 64%** at AR(1) oracle Sharpe 3.9 (32/50 also clear the deflation bar), 34% at oracle 4.0 in the reverting direction, **0%** at oracle 1.3. The earlier 0/50-everywhere result was measured on 3000 bars against a hunt that gets 5400 | `power-calibration.yml` (ADR-041/049/050/051) |
| **Is the effect size those rates are quoted against achievable?** | Not always. Charged the same 10bp turnover cost the catalog pays, the oracle at \|φ\| = 0.10 is **+0.02 / −0.09** — the two zero-power cells contained no tradeable edge at all | `power-calibration.yml` (ADR-055) |
| **Resolution** — what must an edge actually *be* to be found here? | a **true annualized Sharpe of 2.13**, at the current 607-symbol universe and 4.3-year holdout | `scripts/pool_report.py` (ADR-043) |
| How many discovered strategies clear that bar today? | **0 of 40.** They are forward-tested on paper, never recommended | `GET /api/v1/pool-report` |
| **Does what the search proposes beat a no-edge surrogate?** | **No.** Its 603 finalists lose to a bootstrap null built from SPY's own return distribution (p = 1.0000 one-sided, both walk-forward and purged CV) and beat only an iid-normal one | `scripts/pool_report.py` vs `null-calibration.yml` (ADR-051) |

The last two rows are the point. The pipeline has searched 614,000+ parameter trials across 607
symbols and **graduated nothing that is distinguishable from best-of-N selection luck** — and when
the strategies it *proposes* are compared against a surrogate with no serial structure at all, they
do not win either. Walk-forward and purged-CV out-of-sample Sharpes are read against their own
measured null distributions (bootstrap p95 ≈ +0.98 walk-forward, +1.00 purged CV), never against
zero. Because every strategy in the catalog trades serial structure, and the bootstrap null
destroys serial structure while preserving SPY's return shape exactly, the search's advantage over
an iid-normal null is **distributional rather than predictive** (ADR-051).

That is a claim about this universe and this catalog jointly, not about the thresholds. The power
row is what makes it sayable: a gate that detects nothing could not distinguish "no edge here" from
"no ability to see one", and this one detects a planted edge 64% of the time and clears its own
deflation bar 32 times in 50.

Where it still fails is **capture**, and ADR-055 sharpened that considerably by charging the oracle
the same transaction costs every catalog strategy pays. Measured net of costs, the catalog's best
in-sample config *beats* a cost-paying oracle on AR(1) processes (104–126%) and reaches only
**29–45% on band reversion at half-lives 1–5**, where it detects 0%. The fast band cells have a
*higher* net oracle than the AR(1) cell detected 22% of the time (+1.70 vs +1.15), and capture rises
monotonically with the horizon (31% → 58%).

ADR-056/057/058 then took that finding apart. A strategy was added specifically to express fast
reversion to a slow-moving level, the calibration was re-run, and **net capture moved by at most
0.7pp** — so the record now says which strategy won each of the 50 searches per cell. At half-life 1
the search picks a **Trend** strategy 68% of the time on a process that is by construction fast
reversion, and capture tracks that recognition share almost exactly (18% reverting finalists → 32%
capture; 94% → 45–56%). **The gap is recognition, not expression:** at fast half-lives no reverting
strategy wins the in-sample comparison, so the search never gets as far as choosing between them.
Splitting capture by category (ADR-059) makes the size of that plain — at half-life 1 the headline
32% is carried by trend strategies fitting the level, while the reverting strategies keep 22%.

Then ADR-061 asked what was recoverable at all. The planted process is a random-walk level plus a
fast deviation, and only their sum is observable, so the oracle every one of those ratios divided by
knows a state no strategy can see. A Kalman filter given the true process parameters — an upper
bound on any causal price-based strategy — nets **−0.08** Sharpe at half-life 1 against that
oracle's +1.70, and +0.95 at half-life 5. Measured against what is actually recoverable, the catalog
converts **103–105%** of it at half-lives 5–20 and there is nothing to convert at half-lives 1–2.
**The gap was the benchmark, not the catalog** — and the zero detection rate follows from the
detectable-edge frontier alone: a recoverable Sharpe of at most ~0.95 against a ~2.1 requirement. A
gate that graduated any of those cells would have been wrong.
The added strategy was removed once it failed its own pre-stated criterion — that loop, stating a
criterion before the measurement and honouring it afterwards, is the point of the project.

**The same message shows up on real data, in a different place.** ADR-060 records, for every
experiment in the pool, the best in-sample Sharpe achieved by each catalog *category*, so the pool
report can ask whether the family the search selects is separable from the one it passed over.
Across 3,255 experiments the medians are Trend **+0.569** (wins 53% of searches), Breakout **+0.495**
(10%), Mean Reversion **+0.469** (33%), Combination **+0.316** (3%) — and the median lead of the
winning category over the runner-up is **+0.074** against a Lo (2002) Sharpe standard error of
**0.215**. For a typical symbol the *kind* of strategy the search picks is inside a third of one
standard error of the kind it rejected. That is not a defect in the selection rule; it is the same
statement ADR-061 makes on synthetic data — at this history length the data does not contain enough
information to separate these hypotheses, which is why the honest output of the whole pipeline is
still zero graduates.

## What's shipped

End-to-end, all gates green (backend 99.82% coverage, 1,286 tests; frontend 92.6%, 225 tests):

- **15 HTTP endpoints**: health, strategy catalog (single source of truth per ADR-010), ingest,
  bars, backtest, validate, Monte Carlo, plus the research-lab surface — leaderboard, graduates,
  pool report, paper portfolio, equity curve, cross-sectional factors, null calibration, power
  calibration. Sync `def`
  per ADR-009, so blocking yfinance + DB calls go through FastAPI's threadpool.
- **7 product pages**: **Validation Report** (full statistical suite + plain-English verdicts),
  **Data Explorer**, **Backtest Results** (equity curve with buy-and-hold overlay, underwater
  drawdown, rolling Sharpe, return distribution), **Compare Configs**, **Lab dashboard** (the
  deflation headline, the measured gate calibration, the paper book, cross-sectional factors),
  **Discoveries**, **About**.
- **Data layer**: PriceBar / FundamentalData / quality models; yfinance adapter + OHLCV normalizer
  with split/dividend adjustment; 6-active-check DataQualityEngine (honest "flags potential X"
  wording — never "guarantees"); SEC EDGAR fundamentals; **sync TimescaleDB repository on
  psycopg3** with Alembic migration (hypertable + index), Docker-gated integration tests.
- **Research engine**: vectorized pandas/numpy backtester (ADR-007 — vectorbt rejected: fails on
  Python 3.12); **34 single-name strategies** and **10 cross-sectional factors**, each with its
  paper citation in `.claude/context/research-papers.md`; adding a strategy is a single backend
  diff (ADR-010); benchmark comparator; Monte Carlo simulator; experiment manifest.
- **Validation engine**: PBO via CSCV (Bailey 2015), a multiple-testing-adjusted Sharpe margin,
  **scored** walk-forward with Pardo efficiency (ADR-038) and **scored** purged K-fold CV whose
  embargo is sized from the grid's longest lookback (ADR-039), parameter stability, regime
  analysis, universe-level deflation (ADR-018). Every financial-math invariant
  (`docs/ARCHITECTURE.md` §8) is a Hypothesis property test.
- **Autonomous research loop**: sharded daily discovery, weekly cross-sectional and fundamental
  sweeps, and paper forward-testing run as scheduled GitHub Actions with no human in the loop;
  graduates are frozen into a paper book (ADR-019 — paper only, never real money) and retired on
  measured decay.

The engine is calibrated to be honest: a random walk yields PBO ≈ 0.9 and does not pass.

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync, psycopg3),
  TimescaleDB, Alembic
- **Research**: NumPy, SciPy, Pandas — vectorized backtesting on pandas/numpy (ADR-007)
- **Frontend**: React 19 + TypeScript strict, Vite, Tanstack Query 5, Zustand 5,
  Recharts 3, Zod 4
- **Testing**: pytest + Hypothesis (backend); Vitest + React Testing Library + MSW
  (frontend); coverage gates 85% backend / 75% frontend, currently 99.98% / 92.7%
- **Tooling**: uv (Python env), ruff (lint + format), mypy (strict), pre-commit, GitHub
  Actions CI (backend + frontend + pre-commit, gating every commit)

## Layout

```
backend/    FastAPI app, data layer, research engine, validation engine
frontend/   React dashboard (Vite + TS strict + Vitest)
docs/       ARCHITECTURE.md, ADRs (ADR-001..043), C4 diagrams
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
- **Phase 5** (product surface) — done; seven pages shipped end-to-end
- **Phase 6** (autonomous research) — running; scheduled discovery, forward testing, and the
  gate-calibration measurements above. The open question is not "does it find strategies" but
  "is anything it finds distinguishable from luck" — and the answer is currently, honestly, no.
