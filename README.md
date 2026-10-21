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
with it. The table and narrative below retain historical measurements from the cited
procedures and cohorts; they are not measurements of today's default search. The calibration
API and dashboard report recorded/current search, gate and history compatibility (ADR-294).
The live pool report supplies current counts. Historical reference scores and selected
in-sample ratios do not establish optimality or absence of tradeable edge (FINDING-155/159/164).
Frozen measurements retain their identities; these summaries do not authorize another look.

| question | answer | how |
|---|---|---|
| **Type-I error** — how often does the whole pipeline graduate a symbol with *no edge by construction*? | **0/200** under both iid-normal and bootstrap nulls, with ADR-050's dispersion and judged at the hunt's own 7400-bar history (ADR-063). Max DSR -0.368 (iid) / -0.253 (bootstrap) | `null-calibration.yml` (ADR-036/037/050/051/063) |
| Do those false graduates survive the universe-deflation bar? | **0 of 200**, in both nulls | same run |
| **Historical power** — what did the planted-edge procedure detect? | **66%** at AR(1) historical reference Sharpe 3.9 (33/50 also clear the deflation bar), 40% at reference Sharpe 4.0 in the reverting direction, **0%** at reference Sharpe 1.3. The recorded history change to 1990 moved 34/22/14/64% → 40/36/24/66%, with no cell down (ADR-063); this does not prove a general monotonic history effect | `power-calibration.yml` (ADR-041/049/050/051/063) |
| **What did the cost-paying reference earn?** | Charged the same 10bp turnover cost the catalog pays, the historical sign reference at \|φ\| = 0.10 earned **+0.02 / −0.09**. Near-zero scores for that rule do not establish absence of tradeable edge or bounds on other strategies | `power-calibration.yml` (ADR-055; FINDING-155) |
| **Conditional model frontier** — what does crossing one bar require in the stated approximation? | At 80% clearance probability, the historical iid-normal asymptotic model gives **a true annualized Sharpe of 2.13** at the 607-symbol universe and 4.3-year holdout, falling to **1.82** at the 5.9-year holdout from ADR-063. The bar scales as `1/sqrt(T)` in holdout length and `sqrt(ln N)` in universe size. This is not composite pipeline power or a universal minimum edge | `scripts/pool_report.py` (ADR-043/063/292) |
| How many discovered strategies cleared that bar in the reported snapshot? | **0 of 41.** They are forward-tested on paper, never recommended | `GET /api/v1/pool-report` |
| **Does what the search proposes beat a no-edge surrogate?** | **No.** In the 5,400-bar cohort (1,155 matched), walk-forward **+0.532** and purged-CV **+0.575** do not separate from bootstrap medians **+0.652 / +0.661**. In the 7,400-bar cohort (254 matched), **+0.460 / +0.601** likewise do not separate from **+0.617 / +0.639** | `scripts/pool_report.py` vs `null-calibration.yml` (ADR-051/064) |
| **What remained after the paired buy-and-hold control?** | **The measured median excess is near zero on these nulls.** Per symbol on 200 nulls each: walk-forward excess is **−0.011** (bootstrap) and **+0.000** (iid-normal); purged-CV excess is **−0.000** under both modes | ADR-068/078, `null-calibration.yml` |
| **What does the search ADD, with drift removed from both sides?** | Walk-forward adds **−0.127** on 254 matched experiments (89 symbols, 7,346 bars), against **−0.011 / +0.000** on the nulls. Purged CV adds **−0.000** on its first 88-symbol measured cohort, against **−0.000 / −0.000** | `scripts/pool_report.py` (ADR-068/072/078; FINDING-017) |
| **Is that difference distinguishable from the null's?** | **Walk-forward: yes, and in the wrong direction** — **−0.116 [−0.174, −0.064]** against bootstrap and **−0.127 [−0.179, −0.072]** against iid-normal. **Purged CV: no** — **+0.000 [−0.048, +0.002] / +0.000 [−0.048, +0.000]**. These symbol-clustered intervals remain lower bounds on width; ADR-081 pre-registers 400 whole-panel null replicates but has not spent that measurement | `scripts/pool_report.py` (ADR-075/078/081) |
| **Did lengthening the searched history make selection worse?** | **Not decidably.** Paired within symbol across ADR-063's window change, the finalist's out-of-sample Sharpe moved **−0.038 [−0.060, −0.009]** on 368 symbols while in-sample moved **+0.012 [−0.005, +0.034]**, and the search picks a *different strategy* on **257 of 368**. Re-searching 45 of them at the old window to remove the drift confound gives **−0.074 [−0.157, +0.030]** — the interval includes zero, so ADR-074's pre-stated criterion does not fire and the window stays | `scripts/window_experiment.py` (ADR-063/074) |

The historical comparisons show that, with drift removed from both sides, **walk-forward
selection subtracts about 0.12 Sharpe
more on real symbols than on data built to contain nothing, while purged-CV excess is zero and does
not differ from the null.** These comparisons do not establish an edge under either diagnostic; only the
causal walk-forward comparison in these cohorts shows an additional real-versus-null difference.
The reported per-symbol counter snapshot preserves 477,000+
candidate evaluations as the conservative cumulative DSR/MinTRL lower bound (ADR-062/066). The
reported snapshot has **no graduate clearing the best-of-N bar** — and when
the strategies it *proposes* are compared against a surrogate with no serial structure at all, they
do not win either. Walk-forward and purged-CV out-of-sample Sharpes are read against their own
measured null distributions (bootstrap p95 ≈ +0.98 walk-forward, +1.00 purged CV), never against
zero. Because every strategy in the catalog trades serial structure, and the bootstrap null
destroys serial structure while preserving SPY's return shape exactly, the search's advantage over
an iid-normal null is **distributional rather than predictive** (ADR-051).

**ADR-064 made that comparison formally valid for the first time, and it survived.** The
report used to refuse all four comparisons: it required the pool's *median* history to equal the
null artifact's exactly, and a median that grows by one bar per trading day never does. The
comparison now runs on the subset of experiments whose history is within 10% of the null's — 2,427
of them, at a median 5,445 bars against nulls at 5,400, all carrying the null's own search
fingerprint. On that matched subset the pool's walk-forward median is **+0.542** against a
bootstrap null median of **+0.652** (p95 +0.983) and purged-CV **+0.584** against **+0.661**
(p95 +1.003): **the search does not separate from a no-edge surrogate, and against the bootstrap it
sits below the null's median.** The pool-wide median would have read +0.567 — the subset is not a
formality. Those figures are against the 5,400-bar nulls. ADR-063's re-dispatch
briefly replaced them with 7,400-bar ones and the report went to `0 matched` — correctly, since a
pool at 5,445 bars is 26% away from a 7,400-bar null. **ADR-065 fixed the cause rather than the
symptom**: a null artifact is now named for the history it measured (`bootstrap_spy_5400.json`,
`bootstrap_spy_7400.json`), both lengths sit on disk, and a pool in transition is read against each
cohort separately. What changed permanently is the mechanism, not the verdict.

**ADR-068 then found where the level of that number comes from, and it is not the search.** The
walk-forward out-of-sample Sharpe is denominated in the drift of whatever series it was computed on.
Measured: each null's finalist median equals its own generator's buy-and-hold Sharpe to within ±0.03
(iid-normal 0.397 → +0.414; bootstrap:SPY, whose source is SPY 1993→2026, 0.650 → +0.652), and the
matched pool's 0.546 → +0.542. **The −0.11 "gap" above is the gap between SPY's 33-year drift and
the median pool symbol's over its own window.** **The null side is now measured pairwise, not estimated** (run
33287465013, 200 symbols per mode at 7,400 bars): the median per-symbol excess of the finalist over
holding the same series across the same windows is **−0.006** against the bootstrap null and
**+0.000** against the iid-normal one, and the searched finalist beats simply holding only **18.5%**
and **36.0%** of the time — it pays turnover costs for a signal that is not there, exactly as it
should. Controlling for drift also makes the comparison **an order of magnitude more sensitive**:
the bootstrap null's p95 falls from **+0.968 raw to +0.096 in excess terms**, so a real edge no
longer has to out-run the spread of market drift to be visible.

**The real side of that row measured for the first time on 2026-08-31, and it is negative.** Across
the 77 experiments (66 symbols, 7,345 bars) that now carry the paired benchmark and match the
7,400-bar nulls, the median excess is **−0.125**, negative in **75.3%** of them, against **−0.006**
and **+0.000** on the two nulls. **What the search adds out-of-sample over holding the same series
across the same windows is less than what it adds on data with no edge by construction.** The
single-draw verdict rule does not change on it: −0.125 sits at the bootstrap null's 11.5th
percentile, inside its p5 of −0.233, so that row reads *does not separate* — and ADR-072 made the
band two-sided so a reader can see which side of it the number is on.

**ADR-075 then fixed the comparison itself, and the answer flipped.** The band above is over
*individual null draws*: it answers "could one symbol look like this", and one easily could. The
question the row is actually asked is whether the pool's *centre* differs from the null's, and that
needs an interval on the difference of medians — resampled with the real side **clustered by
symbol**, because the 77 excesses come from 66 symbols and are not independent draws. Measured:
**−0.119 [−0.215, −0.061]** against the bootstrap null and **−0.125 [−0.218, −0.063]** against the
iid one, over 66 clusters. **Both exclude zero.** So the honest headline is not "the search does not
separate from a no-edge surrogate" but **"the search separates from a no-edge surrogate in the wrong
direction"** — the strongest evidence here that the in-sample argmax fits structure that does not
persist. Three qualifications ship with that sentence and are printed beside it: the interval is a
**lower bound on its own width** (the symbols share one calendar window, so cross-sectional
correlation survives — FINDING-012 requires independent correlated-panel null replicates, because
one correlated panel followed by symbol-level resampling would repeat the error); the single-draw
verdict is reported unchanged rather than replaced; and ADR-075 discloses that the point estimate
was known before the scheme was fixed, so what was pre-registered is the procedure, not the answer.

That is a historical comparison for the stated universe, catalog and procedure. The power row
separately records a planted-edge detection rate of 66% and clearance of its own
deflation bar 33 times in 50. Those synthetic counts do not certify current-default or
real-market power, and cannot prove absence of other edges or selection methods.

The historical **capture** comparison in ADR-055 charges the stated reference
the same transaction costs every catalog strategy pays. Measured net of costs, the selected
in-sample config scores above that cost-paying AR(1) reference (103–128%) and reaches
**30–42% on band reversion at half-lives 1–5**, where it detects 0%. The fast band cells have a
*higher* net reference score than the AR(1) cell detected 24% of the time (+1.70 vs +1.15), and the ratio rises
monotonically with the horizon (31% → 50%) in these measured cells. Those ratios all *fell* when
ADR-063 lengthened the searched history. Their numerator is an in-sample maximum over the
searched grid, and the history change also changes observations; this comparison does not
isolate the cause or prove a general monotonic history effect. These are selected
in-sample ratios to specified strategies, not fractions of an optimal edge captured.

ADR-056/057/058 then took that finding apart. A strategy was added specifically to express fast
reversion to a slow-moving level, the calibration was re-run, and **net capture moved by at most
0.7pp** — so the record now says which strategy won each of the 50 searches per cell. At half-life 1
the search picks a **Trend** strategy 68% of the time on a process that is by construction fast
reversion, and capture tracks that recognition share almost exactly (18% reverting finalists → 32%
capture; 94% → 45–56%). **This is an observed recognition pattern:** at the tested fast half-lives,
reverting strategies win less often. It does not establish that another strategy or selection
rule could not help, and the recorded 18% reverting share is not zero.
Splitting capture by category (ADR-059) makes the size of that plain — at half-life 1 the headline
32% is carried by trend strategies fitting the level, while the reverting strategies keep 22%.

ADR-061 then measured a different reference. The planted process is a random-walk level plus a
fast deviation, and only their sum is observable, so the oracle every one of those ratios divided by
uses latent information unavailable to a price-only strategy. The specified historical Kalman
recursion with true process parameters nets **−0.08** Sharpe at half-life 1 against the latent
reference's +1.70, and +0.95 at half-life 5. The catalog's selected in-sample ratio to that
filtered reference is **88–98%** at half-lives 5–20; a refused ratio at half-lives 1–2 does not
prove there is nothing to capture. Historical log-mean signs were scored on simple returns,
and the historical startup/posterior was not certified (FINDING-159).
**These are comparisons between specified strategies, not a recoverable-edge bound.**
A reference score of at most ~0.95 versus the conditional single-bar model's ~1.50
after ADR-063 lengthened the holdout (~1.76 before) contextualizes that reference;
it does not prove another causal, cost-aware strategy could not graduate. Later explicit
reference modes (ADR-308/313) do not restate the historical measurements.
The added strategy was removed once it failed its own pre-stated criterion — that loop, stating a
criterion before the measurement and honouring it afterwards, is the point of the project.

**ADR-060 records a separate descriptive comparison on real data:** for every
experiment in the pool, the best in-sample Sharpe achieved by each catalog *category*, so the pool
report can ask whether the family the search selects is separable from the one it passed over.
Across 3,255 experiments the medians are Trend **+0.569** (wins 53% of searches), Breakout **+0.495**
(10%), Mean Reversion **+0.469** (33%), Combination **+0.316** (3%) — and the median lead of the
winning category over the runner-up is **+0.074** against a Lo (2002) Sharpe standard error of
**0.215**. That is a descriptive comparison with an individual-score standard error, not an
uncertainty test for the selected, dependent category difference. As with ADR-061's
reference comparisons, it cannot establish that
the available data cannot separate the hypotheses, explain a graduation count, or rule out
another selection method.

## What's shipped

Recorded build snapshot (backend 98.02% coverage, 1,809 tests; frontend 97.57%, 349 tests):

- **18 HTTP endpoints**: health, strategy catalog (single source of truth per ADR-010), ingest,
  bars, backtest, validate, Monte Carlo, plus the research-lab surface — leaderboard, graduates,
  pool report, paper portfolio, equity curve, cross-sectional factors, null calibration, null
  comparison, window comparison, window experiment, power calibration. Sync `def`
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
  Python 3.12); **34 single-name strategies** and **13 cross-sectional factors** (16 when
  fundamentals scores are available), each with its paper citation in
  `.claude/context/research-papers.md`; adding a strategy is a single backend
  diff (ADR-010); benchmark comparator; Monte Carlo simulator; experiment manifest.
- **Validation engine**: PBO via CSCV (Bailey 2015), a multiple-testing-adjusted Sharpe margin,
  **scored** walk-forward with Pardo efficiency (ADR-038) and **scored** purged K-fold CV whose
  embargo uses the grid's integer-parameter lookback proxy (ADR-039), parameter stability, regime
  analysis, universe-level deflation (ADR-018). Every financial-math invariant
  (`docs/ARCHITECTURE.md` §8) is a Hypothesis property test.
- **Autonomous research loop**: sharded daily discovery, weekly cross-sectional and fundamental
  sweeps, and paper forward-testing run as scheduled GitHub Actions with no human in the loop;
  graduates are frozen into a paper book (ADR-019 — paper only, never real money) and retired on
  measured decay.

The reported random-walk control yielded PBO ≈ 0.9 and did not pass; that observation
does not establish a universal random-walk verdict or current-procedure error rate.

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync, psycopg3),
  TimescaleDB, Alembic
- **Research**: NumPy, SciPy, Pandas — vectorized backtesting on pandas/numpy (ADR-007)
- **Frontend**: React 19 + TypeScript strict, Vite, Tanstack Query 5, Zustand 5,
  Recharts 3, Zod 4
- **Testing**: pytest + Hypothesis (backend); Vitest + React Testing Library + MSW
  (frontend); coverage gates 85% backend / 75% frontend; snapshot above 98.02% / 97.57%
- **Tooling**: uv (Python env), ruff (lint + format), mypy (strict), pre-commit, GitHub
  Actions CI (backend + frontend + pre-commit, gating every commit)

## Layout

```
backend/    FastAPI app, data layer, research engine, validation engine
frontend/   React dashboard (Vite + TS strict + Vitest)
docs/       ARCHITECTURE.md, ADRs (initial ADR-001..043 and later decisions), C4 diagrams
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
  "is anything it finds distinguishable from luck". The historical comparisons above did not
  establish that distinction; current counts and procedure compatibility belong to the live reports.
