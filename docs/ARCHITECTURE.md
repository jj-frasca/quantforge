# QuantForge — Project Architecture Reference
> **This document is a human reference document, not a Claude Code prompt.**
> It lives at docs/ARCHITECTURE.md in the repository.
>
> How to actually use it:
> - Humans: read this to understand every decision made in this codebase
> - Claude Code sessions: start with a SHORT session playbook from .claude/playbooks/
>   The three-tier context system (CLAUDE.md + agents + cold memory) handles
>   everything Claude needs to know persistently between sessions.
>
> Sources: Anthropic official docs (code.claude.com), Vasilopoulos (2026) arXiv:2602.20478,
> Bailey et al. (2015) SSRN:2326253, López de Prado (2018) Advances in Financial ML.

---

## 0.5 Resolved Decisions (post-spec, 2026-05-27)

These resolve inconsistencies in the original spec and are authoritative. Where they
affect a section below, the section has been edited inline to match.

1. **Project location**: `~/claude-work/quantforge/` — standalone, its own git repo
   (default branch `master`). NOT inside `repos/` (that holds UMich coursework).
2. **Primary data source (Phase 2)**: yfinance. No API key, full OHLCV history,
   exercises the adapter pattern when Polygon is added as the second vendor in Phase 3.
   `POLYGON_API_KEY` is Phase 3+ optional (moved out of required Phase 1–2 env — see §10).
3. **CI vs live-data tests**: CI gates on deterministic synthetic fixtures ONLY.
   Live-data tests are marked `@pytest.mark.live` and excluded from the standard CI run.
   (Phase 2 exit criterion in §9 edited accordingly.)
4. **Workflow skills in Phase 1 (hybrid)**: Pre-create only `commit-writer` and
   `tdd-cycle` — they provide execution value beyond a template (draft commit body from
   the diff; run the RED→GREEN→coverage loop). Defer `adr-creator` (ADR-000-TEMPLATE.md
   is sufficient) and `validation-runner` (Phase 4 is months out — speculative now).
   Build the deferred two on demand when the pain recurs.
5. **Citations are load-bearing and verified**: Vasilopoulos (2026) arXiv:2602.20478,
   "Codified Context: Infrastructure for AI Agents in a Complex Codebase" (submitted
   24 Feb 2026; 283 sessions, 19 agents, 34 cold-memory docs; ">50% domain knowledge"
   from the paper body) is real. Path-scoped `.claude/rules/*.md` (YAML `paths:`
   frontmatter) is a native Claude Code feature — build as designed.
6. **vectorbt** — RESOLVED 2026-05-28: rejected. It fails to install on Python 3.12 here
   (numba → llvmlite 0.47.0 native build fails). The backtest engine uses plain vectorized
   pandas/numpy instead (ADR-007). The buy-and-hold oracle test uses an analytic closed-form
   baseline, not a vectorbt comparison.
7. **MVP milestone**: Phases 1–4 + a minimal frontend that renders a real
   `ValidationReport`. Do not build breadth inside a phase before advancing. First
   working ValidationReport is the milestone that matters.
8. **Storage access** — RESOLVED 2026-05-28 (ADR-009): **synchronous** stack on the psycopg
   (psycopg3) driver — SQLAlchemy 2.0 sync engine/sessions, FastAPI DB routes as sync `def`
   (threadpooled). Rationale: localhost DB + low concurrency + blocking yfinance mean async
   adds complexity for no real gain (async wins on *remote* I/O under *high* concurrency).
   This supersedes the "async" detail of ADR-002; psycopg3 keeps an async migration path open.
9. **Frontend = React 19** (Phase 5, 2026-05-28): the spec said React 18, but `npm create vite`
   and the current stable ecosystem are on **React 19** (with TS strict, Vite + Vitest, Tanstack
   Query 5, Zustand 5, Recharts 3, Zod 4). Component code is materially identical; using the
   current stable is the better engineering choice. Frontend tests run on Vitest + RTL + MSW;
   coverage gate ≥ 75%.

## 0.6 Implementation Status (as of 2026-06-30 — SUPERSEDED IN PART, see §0.6.1)

The §4 tree below is the **target** layout; not all of it is built yet. Authoritative reality:

**BUILT & tested (100% backend coverage; frontend ≥75%):**
- Data layer: PriceBar / FundamentalData / quality models; `DataSourceAdapter` ABC +
  `YFinanceAdapter` + `OHLCVNormalizer`; `DataQualityEngine` (6 active heuristic checks — see
  below); `DataIngestionPipeline` + in-memory `PriceBarRepository`; SQLAlchemy ORM models;
  **TimescaleDB sync repository (psycopg3) + Alembic migration** (hypertable + index),
  integration-tested via Docker (`make migrate`, `make test-integration`).
- Research: vectorized `BacktestEngine` + metrics + §8 oracle tests; **11 strategies** in
  the catalog (`STRATEGY_CATALOG` in `app/research/strategies/catalog.py`, ADR-010 is the
  single source of truth) grouped into Trend / Mean Reversion / Breakout / Combination —
  SMA, Momentum, Mean Reversion z-score, RSI Mean Reversion, Donchian Breakout, Bollinger
  Bands, MACD, Vol-Targeted SMA, Keltner Channel, Trend-Filtered Mean Reversion, Triple MA
  Alignment; `BenchmarkComparator`; `MonteCarloSimulator`; `ExperimentManifest`.
- Validation: `deflated_sharpe`, `pbo` (CSCV), `walk_forward`, `purged_cv`,
  `parameter_stability`, `regime_analysis`; `ValidationEngine` → `ValidationReport`.
- API: 7 endpoints — `GET /health`, `GET /api/v1/strategies` (catalog: each entry has
  category + label + description + citations + ParamSchema, ADR-010), `POST /api/v1/ingest`
  (runs `DataIngestionPipeline` behind DI), `POST /api/v1/validate` (**cache-aside** through
  the repo; auto-generated grids per catalog entry; returns plain-English `Interpretation`s
  per metric), `GET /api/v1/bars` (read-only projection of cached bars — float `ChartBar`
  for charting), `POST /api/v1/backtest` (single-config backtest, cache-aside; customizable
  `initial_capital` + `cost_rate`; returns equity + buy-and-hold + drawdown + rolling-Sharpe
  curves + daily-return distribution + **trade_markers** for the chart overlay + **nullable
  `benchmark_comparison`** (alpha/beta/IR/tracking-error vs SPY, ADR-013); discriminated
  `StrategyConfig` over every catalog entry), `POST /api/v1/monte-carlo` (ADR-014 Phase 0 —
  runs the strategy then GBM-simulates forward risk: P(terminal loss > X), P(max drawdown > X),
  terminal-return percentiles; deterministic under `seed`; wires the previously-dead
  `MonteCarloSimulator`).
  Frontend: **Data Explorer** (form → `/ingest` → `IngestResultView` + Recharts price chart
  from `/bars`), **Backtest Results** (catalog-driven per-strategy param form with inline
  hints → `/backtest` → metrics + four canonical charts: equity-with-buy-and-hold AND
  trade-marker triangles, underwater drawdown, rolling Sharpe, return-distribution
  histogram + a **benchmark-vs-SPY panel** (alpha/beta/IR, ADR-013) below the equity curve),
  **Validation Report** (symbol/strategy/range form → `/validate` → metrics +
  Interpretations panel + flags), **About** (live-rendered catalog grouped by category +
  validation methodology + ADR links — the project's own self-documenting page). Strategy
  dropdowns on the form pages are grouped by category via `<optgroup>`. 4-way primary nav
  (Data Explorer default); CI gates backend + frontend.

**DEFERRED / NOT YET BUILT (documented in the target tree but absent in code):**
- **Redis cache** — only a `redis_url` config field exists; no client/cache code. The
  cache-aside store today is TimescaleDB itself; Redis is for hot-path/intra-request memoization.
- **`experiment_store.py`** — not built; `ExperimentManifest` lives in `backtesting/manifest.py`.
- **Polygon adapter** — Phase 3+; only the `Source` enum value exists, so **vendor
  cross-validation** (check #8) cannot run. **Corporate-action detection** (check #3) is also
  not implemented yet. Active `DataQualityEngine` checks: `insufficient_data` (error),
  `survivorship_risk` (info), `missing_bars`, `price_anomaly`, `stale_data`,
  `split_dividend_consistency` (warnings). Timezone (#7) is enforced at the PriceBar boundary
  (raises), not as a soft flag.
- **Frontend pages**: `validation-report`, `data-explorer`, and `backtest-results` are built;
  `strategy-config` is still an empty dir (Backtest Results already takes per-strategy params
  via its discriminated form — the separate page may be unnecessary).
- **`Portfolio`** is NOT a separate class — position/cost/equity math lives in `BacktestEngine`.
- Deferred skills (`adr-creator`, `validation-runner`) and the `database-migrations.md` rule
  are listed in §4 but intentionally not created yet.

Synthetic fixtures are a **single `tests/fixtures/synthetic/builders.py`** module (functions
like `clean_series`, `with_split`, `regime_shift_series`), not the per-file layout in §4/§8.

## 0.6.1 What changed since 2026-06-30 (read this before trusting §0.6)

§0.6 above is a **historical snapshot** and is now materially out of date — it predates the entire
autonomous-research half of the project. Read this section for current reality; ADRs are the
authority, and `docs/adr/` is complete.

**The autonomous research loop (the biggest change).** QuantForge now searches on its own, in the
cloud, for free:
- **`app/research/lab/`** — `run_search` (coarse-to-fine parameter search), `GraduationGate`
  (DSR / PBO / parameter stability / MinTRL / locked holdout / beat-buy-and-hold), `run_universe_hunt`
  across a symbol universe, the `Experiment` research pool, `hunt_and_promote`, and the managed
  paper book (`portfolio_manager`, ADR-019/020). **34 strategies** in `STRATEGY_CATALOG`, not 11.
- **`app/research/cross_sectional/`** (ADR-024/025) — a second, orthogonal dimension: rank the whole
  universe each period into dollar-neutral long/short legs, judged by the SAME gate. Includes
  forward-testing and a lifecycle book.
- **`app/research/fundamentals/` + `app/research/valuation/`** (ADR-022/023/029) — EDGAR-sourced
  quality (Piotroski F-score, Novy-Marx gross profitability), valuation scoring, a financial-distress
  screen, and a weekly sweep over ~10.4k SEC filers.
- **`.github/workflows/`** — the loop runs itself: `daily-discovery.yml` (10 sharded jobs over a
  610-name universe, weekdays), `hunt.yml` (weekly), `cross-sectional-hunt.yml`, `paper-forward.yml`,
  `paper-broker.yml` (Alpaca **paper only**, ADR-021), `fundamental-sweep.yml`. Public repo =
  unlimited Actions minutes, so discovery is token-free (ADR-026).

**Data files under `data/` are generated state and part of the record** — `research_pool/` (per-symbol
partitions, ADR-032), `paper_portfolio.json`, `equity_curve.json`, `cross_sectional_pool.json`,
`fundamentals_pool.json`. **The cloud workflows are their single writer** (ADR-030); never add a
second one.

**Operational invariants learned the hard way (2026-08-18):**
- yfinance rate-limits GitHub-runner IPs at the session bootstrap. Every cloud driver must use the
  shared `CLOUD` retry policy in `app/data/sources/retry.py`, and a shard whose yield collapses must
  **fail loudly** rather than report a green no-op (ADR-031).
- The research pool is partitioned per symbol because a single JSON file hit GitHub's 100 MB push
  limit (ADR-032). Retention lives in the store, so every writer is bounded.
- The honest headline is `scripts/pool_report.py`: as of 2026-08-18, **0 of 40 graduates clear the
  ADR-018 universe-deflation bar**. The paper book records that verdict per position (ADR-033) and
  the dashboard leads with it. Meta-labeling is declined until a primary graduate clears it (ADR-034).
- Every cross-sectional trial records its **rank IC** — the per-date Spearman correlation between the
  signal and next-period returns (ADR-035). A dollar-neutral Sharpe cannot distinguish a factor from
  two lucky names; the IC can. Diagnostic only: nothing gates, selects, or sizes on it.

**The gate's Type-I error is measured, not assumed (ADR-050 refresh landed 2026-08-20, run
32354284731).** `null-calibration.yml` runs the UNMODIFIED search over 200 symbols per null mode
with no edge by construction (ADR-036/037), and commits the answer to `data/null_calibration/`.
Under the production-parity ADR-046/047/048 procedure **with ADR-050's IQR dispersion**, and judged
at the hunt's own 5400-bar history rather than the old 3000 (ADR-051), measured Type-I error is
**0/200 on both nulls**, with max DSR **-0.415** (iid) and **-0.269** (bootstrap). The earlier 1.0%
/ max +0.92 result describes the pre-accounting, uncapped selector only. The repaired composite is
conservative on known-false series; power determines what that conservatism can actually detect.

**Walk-forward and purged CV are real as of 2026-08-19 — they used to be counts.** `ValidationReport`
carried `n_walk_forward_splits` / `n_purged_folds` and nothing was ever trained or scored on those
splits. Now `walk_forward_evaluate` (ADR-038) selects on each expanding train block and scores the
block that follows — the only causal out-of-sample number besides the locked holdout, and the only
one that measures the *selection procedure* — and `purged_cv_evaluate` (ADR-039) scores the purged
folds with an embargo sized from the grid's longest lookback instead of a fixed 2 bars. Both are
**diagnostics with explicit revisit triggers, and neither gates anything**; both are recorded per
`Trial` and summarized by `scripts/pool_report.py` against the null. Their null distributions put
"indistinguishable from noise" at roughly **+1.0 annualized**, and purged CV sits above walk-forward
because its selection sees the future — read them side by side, never averaged. Details:
`.claude/context/validation-methodology.md` §3–§5.

**Their revisit trigger has now fired, and the answer is no separation (ADR-051, 2026-08-20).**
The diagnostics were read only off gate passers while the null artifacts record the finalist of
every searched symbol — two different statistics — and ADR-046's repaired denominator then emptied
the gate-passer set entirely (603 experiments, **0 graduates**). `PoolReport` now summarizes both
windows. On the matched comparison (same search and gate fingerprints, both sides at 5400 bars) the
real universe's 603 finalists reach a median walk-forward OOS Sharpe of **+0.561** against
**+0.652** for the bootstrap null and **+0.414** for the iid-normal null; purged CV reads
**+0.597** against **+0.661** and **+0.475**. Mann-Whitney one-sided for real greater than null:
**p = 1.0000 versus bootstrap on both statistics, p < 0.0001 versus iid-normal on both.** Every
catalog strategy trades serial structure and the bootstrap null has none by construction while
preserving SPY's return shape exactly, so the search's advantage over the iid-normal null is
**distributional, not predictive**. This is not an argument about any threshold, and it is not
"the catalog cannot capture serial structure" — ADR-042 measured 42% detection on a planted
half-life-5 reversion. Four limitations are stated in ADR-051 §Measured.

**The gate's POWER is measured too, and it reframes "0 of 40" (refreshed 2026-08-20 at the hunt's
own history, runs 32355803804/32355806443).** A Type-I error alone cannot say whether "0 of 40
graduates clear the bar" is a fact about the strategies or about the bar. At production parity —
whole-search accounting, production refinement, the enforced candidate budget, ADR-050's dispersion
— and at 5400 bars, the gate detects a planted AR(1) edge **64% of the time at oracle Sharpe 3.9
(32/50 also clear the ADR-018 bar)**, 34% at oracle 3.97 in the reverting direction, 22%/14% at
oracle ≈ 2.6, and 0% at oracle ≈ 1.3 — which is what ADR-043's frontier predicts. **The intermediate
"0/50 in every cell" result was an artifact of measuring on 3000 bars** (ADR-051); it is superseded
and must not be requoted. The remaining zero is band reversion: 0% at every half-life at oracle
≈ 2.6, with DSR passing 0/50, while capture is 20.7–37.2% against 55.1% for AR(1) at the same
oracle. That is a capture gap — a statement about what the catalog can express, not about the
statistics — and it is the first calibrated result that points at a concrete strategy-design action
rather than at the gate. FINDING-005/ADR-049's per-component pass counts are what make it
attributable: DSR passes 0/50 in every band cell and 39/50 for AR(1) at the same oracle, so the
rejection is priced selection acting on a smaller captured Sharpe, not a different component
failing. FINDING-006 (dispersion contaminated by the planted signal) and its ADR-050 IQR repair are
included in every number quoted here. **ADR-053 commits both sweeps to `data/power_calibration/`
and serves them at `GET /api/v1/power-calibration`,** so this curve no longer survives only as
transcribed prose — which is how the superseded zero propagated.

**ADR-055 corrected the denominator those capture numbers are taken against.** The oracle was scored
cost-free while every catalog finalist pays 10bp on turnover, and the oracle is a *sign* strategy
turning over up to 1.19 per bar. Charged the same cost, two readings change. The zero-power cells at
|φ| = 0.10 have a net oracle of **+0.02 / −0.09** against a Sharpe standard error of ≈0.22 — they
contained no achievable edge, so "0% at oracle ≈ 1.3" was never a miss. And at net accounting the
catalog's in-sample finalist *beats* a cost-paying oracle on AR(1) (net capture **104–126%**, the
clearest possible demonstration that ADR-045's ratio is an upper bound, not a fraction achieved)
while reaching only **29–45% on band reversion at half-lives 1–5**. The band gap therefore survives
both corrections and gets sharper: those fast band cells have a HIGHER net oracle (+1.70) than the
AR(1) cell detected 22% of the time (+1.15), and capture rises monotonically with the horizon
(31% → 58%). A capture ratio is refused outright when the net oracle sits inside its own standard
error, so a cell with no achievable edge reports no fraction rather than a ratio against noise.

**ADR-056/057/058 resolved what that gap actually is, and it is not what the wording above implied.**
ADR-056 added `two_timescale_reversion` — a strategy whose entire design is to estimate the level and
the deviation on independent timescales — and re-dispatched all three calibrations. Type-I error
stayed 0/200 on both nulls; net capture moved ≤ +0.7pp in every band cell; detection stayed 0/50.
ADR-057 then made the reading attributable by recording which strategy won each searched symbol, and
the answer is decisive: at half-life 1 the max-DSR search selects a **Trend** strategy 68% of the
time, and the share of *Mean Reversion* finalists (18% / 44% / 64% / 94% / 94% / 82% across
half-lives 1–20) tracks net capture (32% / 30% / 31% / 45% / 56% / 58%) almost exactly. The AR(1)
control recognizes perfectly. **The fast-half-life gap is a RECOGNITION failure — at those horizons
no reverting strategy wins the in-sample comparison, so adding reverting strategies cannot help.**
ADR-059 then split capture by the kind of strategy that earned it, and the fast cells change
meaning: at half-life 1 the headline 32% is carried by **Trend at 31%** (fitting the random-walk
level, 83% of return variance there) while everything aimed at the planted reversion keeps **22%**.
From half-life 3 the matched row is the headline. Quote 22% for what the catalog's reverting
strategies keep of a fast planted reversion. **ADR-061 then retired the finding entirely.** The band oracle is computed from the process's LATENT
deviation and only the level-plus-deviation SUM is observable, so no causal strategy could ever have
reached it. A Kalman filter given the true parameters — the upper bound on any price-based strategy
— nets −0.08 / +0.22 / +0.51 / +0.95 / +0.93 / +0.70 at half-lives 1 / 2 / 3 / 5 / 10 / 20 against a
latent oracle of +1.70 to +2.21. Capture against what is recoverable is **103–105% at half-lives
5–20**, 130% at 3, and refused at 1. The catalog converts essentially everything convertible; the
0/50 detection follows from ADR-043's frontier alone (recoverable ≤0.95 against a ≈2.1 requirement),
with no reference to the catalog. Two follow-ups are closed by the same measurement: a better
estimator cannot help (Kalman and a naive EWM residual correlate with the truth equally at the
production shares) and no alternative selection rule recognizes the matched family more often.
ADR-058 removed the probe strategy for failing its own pre-stated criterion (restoring
`search_config_version 3f36fda2…`, so the committed calibration artifacts apply unchanged) and
points the next unit at the selection step, judged against the finalist category mix.

**ADR-060 answers that on real data, and the answer is the same one.** The pool report now groups
every experiment's trials by catalog category and reports the winning category's median lead over
the runner-up against Lo (2002)'s Sharpe standard error. Over 3,255 pooled experiments: Trend
+0.569 (wins 53%), Breakout +0.495 (10%), Mean Reversion +0.469 (33%), Combination +0.316 (3%), and
the **median lead is +0.074 against an SE of 0.215 — inside one standard error**. The *kind* of
strategy the search selects is not distinguishable from the kind it rejected, on real symbols, for
the same reason ADR-061 gives on synthetic ones: at this history length the data does not separate
the hypotheses. That points the next unit at **holdout length**, not at the selection rule.

**The first measured selection-rule alternative did not replace the default (ADR-069/070), and its
artifact extraction is repaired by ADR-071.** Ranking families by walk-forward OOS Sharpe moved
AR(1) detections only 63/200 → 66/200 across the four cells with recoverable edge and decreased one
cell, failing the pre-stated criterion; production therefore still selects by observed Sharpe.
FINDING-010 later showed that calibration correctly gated the walk-forward-selected family but
reported max-DSR finalist diagnostics and attribution. ADR-071 routes every finalist-level field
through the requested rule. Detection and Type-I counts from ADR-070 remain valid; its non-default
diagnostic observation requires a corrected rerun before reuse. No generated artifact changed.
ADR-079 closes the corresponding persisted-real-side gap: new experiments store the exact selected
trial index (a family name is ambiguous after refinement), and pool reporting uses that checked
identity for every finalist-level statistic. Legacy rows remain max-DSR rather than receiving an
invented selection identity.

FINDING-007 is **resolved** (ADR-054): the paper's probability-form DSR is implemented, every
user-facing claim now calls the stored value a selection-adjusted Sharpe *margin*, and every new
trial records both. What remains is the threshold question — whether the gate should switch to the
probability — which needs a fresh Type-I error and power curve for the new statistic and its own
ADR. `PoolReport.statistic_agreement` measures the two statistics' disagreement so that case can be
made with numbers.

**The detectable-edge frontier (ADR-043) factors those two numbers.** `app/research/lab/frontier.py`
solves `SR_true = bar(N, T) + z_p · SE(SR_true)` with Lo (2002)'s standard error — which at SR = 0
is exactly the `sqrt(1/T)` the ADR-018 bar already uses. At the current design (607 symbols, 4.3y
holdout) an edge must be a **true annualized Sharpe of 2.13** to be found 80% of the time. Measured
power is lower than that frontier, and the gap is the catalog's *capture efficiency*. ADR-045 now
records the max-DSR finalist's in-sample Sharpe for every searched power-calibration symbol and
reports median finalist / median oracle as a selection-biased **upper bound** on capture. Measured
gross capture is 0.21–0.25 at 1–3 bar reversion half-lives and 0.37 at 5 bars (0.32/0.31/0.45 net of
ADR-055's cost correction); the 2-bar configs are searched but do not win, so the fast-reversion
weakness is estimation, not a missing short window.
The design lever this exposes: the bar moves as `sqrt(2 ln N)` in hypotheses but `1/sqrt(T)` in
holdout length, so **halving the universe buys ~4% while doubling the holdout buys ~29%** — history
is the stronger lever by an order of magnitude. `scripts/pool_report.py` and the dashboard print
the frontier beside the deflation headline; none of it licenses moving a threshold (charter §4).
**ADR-063 spends that lever.** The search window was a `datetime(2005, 1, 1)` literal copied into
nine drivers — `T` was a constant, not a property of the data. `app/research/lab/history.py` now
defines it once: `SEARCH_HISTORY_START` = 1990-01-01 for the single-name hunt and the calibrations
that must mirror it, `RECENT_HISTORY_START` = 2005-01-01 for the paper book and everything else that
only needs a recent tail, and `CALIBRATION_N_BARS` = 7,400 so the null cannot silently be judged on a
different length than the hunt (ADR-051). Median searched history 5,448 → 7,444 bars, holdout 4.3y →
5.9y, required true Sharpe **2.13 → 1.82**. Nothing in `GateConfig` moves and `gate_config_version`
is unchanged — the bar is recomputed from `(N, T)` per symbol on every run, and it rises again the
moment the universe grows.

**ADR-064 is the repair ADR-063 forced.** The real-vs-null comparison required the pool's *median*
history to equal the null artifact's exactly — a median that grows a bar per trading day never does,
so the report had been printing `NOT COMPARABLE -- history 5444 bars vs 5400` on all four rows while
2,427 of 3,028 experiments sat within 10% of the null. `compare_with_null` now summarizes the real
side over the experiments whose `n_bars` is within `HISTORY_TOLERANCE` of that artifact's, reports
`matched_n` beside every median, refuses below `MIN_MATCHED = 30`, and applies the search-family
test to the same subset. **The first formally valid comparison this project has produced says the
pool does not separate from either null**: matched walk-forward **+0.542** against a bootstrap
median +0.652 (p95 +0.983), purged-CV **+0.584** against +0.661 (p95 +1.003). It is the deflation
headline's conclusion reached by an independent route, and it is now a measurement rather than an
absence of one. Those figures are against the 5,400-bar nulls, which ADR-063's
re-dispatch briefly overwrote — **ADR-065 removed that failure mode**: an artifact is named for the
history it measured (`bootstrap_spy_5400.json` / `_7400.json`), both lengths coexist, and the pool
in transition is read against each cohort separately instead of being refused.

**ADR-068 attributes the level of that statistic, and the answer is drift.** The walk-forward OOS
Sharpe is denominated in the drift of the series it was computed on: each null's finalist median
equals its own generator's buy-and-hold Sharpe to within ±0.03 (iid-normal 0.397 → +0.414;
bootstrap:SPY 0.650 → +0.652), and the matched pool's 0.546 → +0.542. **ADR-064's −0.11 gap is the
gap between SPY's 33-year drift and the median pool symbol's**, not a difference between two
searches. `walk_forward_evaluate` now scores buy-and-hold across the SAME test blocks
(`mean_oos_hold_sharpe`), `Experiment.walk_forward_hold_sharpe` and
`NullCalibration.walk_forward_hold_sharpes` persist it, and `compare_with_null` emits a
`walk-forward excess` row beside each raw row — the raw row stays, because a published verdict is
not restated on a new statistic in place. **Measured pairwise on both nulls** (run 33287465013, 200
symbols per mode at 7,400 bars): median per-symbol excess **−0.006** (bootstrap) and **+0.000**
(iid), the finalist beats holding only 18.5% / 36.0% of the time, and `corr(OOS, hold) = 0.884` on
the bootstrap null. The excess is also a tighter instrument — bootstrap p95 falls from +0.968 raw to
**+0.096** — so the drift-controlled comparison is roughly an order of magnitude more sensitive than
the raw one. The verdict does not move; what moves is what the number means.

**ADR-072: the real side measured on 2026-08-31, and it is negative.** 77 experiments (66 symbols,
7,345 bars) now carry the paired benchmark and match the 7,400-bar nulls: median excess **−0.125**,
negative in **75.3%**, against −0.006 / +0.000 on the nulls. **What the search adds out-of-sample
over holding the same series across the same windows is less on real symbols than on data with no
edge by construction.** ADR-072 made the band two-sided for that row only — `null_p5` and
`real_below_null_p5`, the latter False *by construction* on the raw rows, whose lower tail is a
drift difference rather than a result — so the report can express a real median under the null
instead of printing the same sentence it would for one just above. The verdict is unchanged:
−0.125 sits inside both nulls' p5 (−0.233 / −0.251).

**ADR-075 fixed the comparison and the answer flipped.** That band is over INDIVIDUAL null draws —
it answers "could one symbol look like this", and one easily could. The row is asked whether the
pool's CENTRE differs from the null's, which needs an interval on the difference of medians with the
real side **clustered by symbol** (77 excesses from 66 symbols are not independent draws). Measured:
**−0.119 [−0.215, −0.061]** vs `bootstrap:SPY` and **−0.125 [−0.218, −0.063]** vs `iid_normal` over
66 clusters — **both exclude zero**. The project's central claim is therefore no longer "the search
does not separate from a no-edge surrogate" but **"it separates in the wrong direction"**: it
subtracts ~0.12 Sharpe more on real symbols than on data built to contain nothing. Reported BESIDE
the single-draw verdict, never in place of it (ADR-068's rule). Three qualifications are printed
with it and must never be dropped: the interval is a **lower bound on its own width** because the
symbols share one calendar window — FINDING-012 says the repair needs **independent correlated-panel
null replicates** (one correlated panel followed by symbol-level resampling repeats the independence
error) and therefore changes both generation and ADR-037's sharding; the single-draw verdict is
unchanged; and ADR-075 discloses that the point estimate was known before the scheme was fixed, so
the pre-registration covers the procedure, not the answer.

**Refreshed 2026-08-31 (session #18) as the 7,400-bar cohort grew, and the effect held.** The
standing watch item on this row was what it would do as the re-searched cohort matured. It has more
than doubled — **n = 166 excesses over 89 symbol clusters**, up from 77 over 66 — and the answer is
stable while the interval TIGHTENS: real median **−0.127** (was −0.125), difference of medians
**−0.122 [−0.191, −0.067]** vs `bootstrap:SPY` (was −0.119 [−0.215, −0.061]) and **−0.127
[−0.194, −0.068]** vs `iid_normal` (was −0.125 [−0.218, −0.063]). Both still exclude zero, and the
bootstrap interval's width fell from 0.154 to 0.124. A point estimate that does not move while its
sample doubles is the behaviour of an effect, not of a fluctuation — contrast ADR-076's look 1,
where −0.074 at n=45 collapsed to −0.008 at n=200.

**But this row is a REPORT LINE, not a test, and the distinction is load-bearing.** It is recomputed
every time `pool_report.py` runs, against a pool that grows daily, so it is read an unbounded number
of times with no spending rule. Its band is therefore **descriptive**. Any *decision* taken on it —
changing a threshold, declaring the direction settled, acting on the sign — needs its own ADR with a
pre-stated criterion, an estimator, and a boundary, exactly as ADR-076 did for the window question.
Quoting the refreshed numbers is fine; treating them as a test that fired is not. ADR-075's three
qualifications above still apply in full, the width is still a lower bound, and the single-draw
verdict is still `does not separate`.

**ADR-074: ADR-063's second clause was unanswerable as phrased, and is now read paired within
symbol.** A holdout Sharpe lives on a graduate and the live family has produced one in 3,029
experiments, so "the pool's median holdout Sharpe must not fall" has no sample. `compare_search_windows`
differences each symbol's finalist across the 6,000-bar window split instead — the cross-symbol form
was measured and rejected, since `n_bars` tracks listing age under one family and the two cohorts
share zero symbols. On 368 symbols the OOS delta is **−0.038 [−0.060, −0.009]** against an in-sample
delta of +0.012 [−0.005, +0.034], and the finalist strategy changes on **257 of 368**. That is a
surrogate — both sides carry their own window's drift — so ADR-074 pre-stated a criterion and
`scripts/window_experiment.py` re-searched 45 symbols at `PRE_ADR063_SEARCH_START`: the
drift-controlled delta is **−0.074 [−0.157, +0.030]**, the interval includes zero, the criterion does
not fire and the window stays. Served at `GET /api/v1/window-comparison`. (That live row now reads
**−0.034 [−0.054, −0.005] over 422 symbols**, the finalist changing on 296 of them, as the pool has
grown — the same surrogate, moving barely at all. **ADR-076 is the answer to it, and ADR-076 is
frozen at its own 200 symbols**: do not re-derive the controlled number from the grown pool, which
would be a third look on a closed sequence. ADR-077's separate endpoint exists for exactly that
reason.)

**ADR-076 spent the second look, and the window change's OOS penalty turns out to be drift.**
ADR-074's n = 45 was under-powered *by choice* — the candidate set held 368 all along and 45 was a
command-line argument (FINDING-013). ADR-076 froze a 200-symbol sample to
`data/window_experiment/adr076_sample.json` and committed it before searching any of it, sized n
from look 1's dispersion (≈87% power), and pre-stated a **Pocock two-look boundary, nominal
two-sided α = 0.0294**, so the two looks together still spend 0.05. All 200 were searched on
2026-08-31 and all 200 carried the benchmark at both windows. **The drift-controlled excess delta is
−0.008 [−0.055, +0.022]: the criterion does not fire, ADR-063's window stays, and the sequence is
closed.** The informative part is the contrast on the same symbols — the raw OOS delta is still
−0.037 [−0.061, −0.008], excluding zero, and subtracting what holding the same series across the
same windows earned collapses it to −0.008 covering zero. **The longer window's apparent
out-of-sample penalty is an artifact of the two windows spanning different market history, not
something the search does**; the finalist still changes on 258 of 368 symbols. |δ|/SE ≈ 0.45 against
a boundary of 2.178, so this is a measured null rather than a failure to resolve.

**ADR-078 finishes the audit ADR-076 implied, and finds exactly one uncontrolled headline.**
ADR-076 showed that on the SAME 200 symbols a raw statistic excluded zero (−0.037 [−0.061, −0.008])
while its drift-controlled version covered it (−0.008 [−0.055, +0.022]) — so every published number
was re-read against one question: *what does this read on data with no edge by construction, and is
that level subtracted?* Everything else is controlled — ADR-055/061 charge the capture ratios their
cost and their achievable oracle, ADR-060's category lead is differenced within symbol, ADR-075's
interval is built on the controlled statistic — but the **purged-CV row of `compare_with_null` was
raw**, next to a walk-forward row that ADR-068 had controlled. ADR-068 deferred it because
"purged-CV's folds are not a prefix-ordered benchmark window"; that reason does not survive, since
fold ordering is a fact about SELECTION and buy-and-hold has no config to select. `purged_cv_evaluate`
now takes the same `benchmark` and reports `mean_oos_hold_sharpe` over the folds it KEPT, and a
`purged-CV excess` row is emitted beside the raw one. Purged CV tests every index once, so its
control covers the whole searched window where walk-forward's covers a suffix — the two hold Sharpes
are separate fields and neither may stand in for the other. Nothing gates on either statistic and no
threshold moves. The 7,400-bar nulls and the first 88-symbol matched real cohort now carry the
control (FINDING-017). Real paired excess is **−0.000**; its clustered difference from bootstrap is
**+0.000 [−0.048, +0.002]** and from iid-normal **+0.000 [−0.048, +0.000]**. Both span zero: purged
CV adds no measured performance beyond holding the same series, and its real excess does not
separate from the null's. The retained 5,400-bar null cohort remains correctly unmeasured.

**ADR-063 is measured, and its own criterion failed while power rose.** At `n_bars=7400`: Type-I
error unchanged at 0/200 on both nulls (max DSR −0.261 / −0.368, `deflation_bar` 1.343 against
1.722), and AR(1) detection moved **34/22/0/0/14/64% → 40/36/0/0/24/66%** for φ = −0.3…+0.3 — four
of four cells that had an edge to find, none down, on a deterministic sweep. The cells ADR-063
named (φ = ±0.1, band half-lives 3–5) stayed at 0%, so the pre-stated criterion is recorded as
**failed**: it lumped "0% for want of power" together with "0% because ADR-061 showed there is
nothing recoverable there". Band capture also *fell* (32/29/31/45/56/58% → 31/30/30/42/51/50%,
and 105/103/104% → 97/98/88% against the achievable oracle) — capture's numerator is an in-sample
maximum, so 1,600 more bars regress it toward truth. **The older, higher ratios were the more
selection-biased ones.**

**The backend gate runs in parallel (ADR-040).** `make test` uses `pytest -n auto`; `make check`
went 8:45 → 4:01. Tests must therefore be order-independent and must not write fixed paths.

**DSR prices the whole search as of ADR-046.** The original StrategyLab reduced each family grid to
one stored finalist, counted those summaries as lifetime trials, and then compared family-local
DSRs. A 34-family full-catalog run therefore recorded 34 trials after evaluating 667 concrete
configs, and prior searches never reached DSR. New longitudinal and cross-sectional runs count every
evaluated config, use cumulative lifetime N plus the whole current search's Sharpe dispersion, and
apply one comparable haircut before the cross-family argmax. `Trial.n_evaluated_configs` preserves
the denominator without bloating the partitioned pool; historical longitudinal counts remain a
lower bound because generated records cannot be honestly reconstructed. FINDING-003 separately
recorded that `GateConfig.trial_budget=200` was inert.

**Daily shards carry the lifetime denominator forward (ADR-062), and reports count it once
(ADR-066).** Each shard writes only its own artifact but reads the committed partitioned pool as a
prior, so DSR/MinTRL no longer reset on every daily hunt. Because every experiment's
`lifetime_trials` already includes that prior, the programme-wide headline sums only the maximum
counter per symbol. Summing all retained cumulative rows would double-count earlier trials; the
headline is the sum of per-symbol denominators, not one global DSR denominator.

**Whole-search dispersion is robust as of ADR-050.** Sample standard deviation made the supposed
null haircut grow without bound when a subset of heterogeneous strategies captured a planted edge;
DSR consequently passed 0/50 even at median oracle Sharpe +3.92. Whole-search pricing now estimates
the Normal trial scale from the central IQR (with sample-standard-deviation fallback below four
candidates). The candidate count, cumulative lifetime N, common cross-family price, and every gate
threshold are unchanged. Fresh Type-I and power calibration is required for the new identity.

**The candidate budget is enforced as of ADR-048.** Longitudinal and cross-sectional searches
canonicalize requested families, reserve two PBO-capable configs for each, and water-fill remaining
capacity fairly instead of letting high-dimensional Cartesian grids dominate. Oversized family
grids are reduced with deterministic maximin parameter-space coverage. Adaptive refinement counts
as one additional family bucket inside the same cap, so coarse plus refined work never exceeds 200
by default. A budget too small to preserve every requested family's PBO minimum fails before any
backtest; reordering or duplicating strategy names cannot change the searched hypotheses.
The post-change cloud refresh measured 0/200 false graduates in each null mode. Its companion 0/50
power result was superseded within hours by ADR-051's history-length repair — the identity was
right and the measurement was too short.

**Calibration now includes production refinement (ADR-047).** Daily discovery performs an adaptive
second grid around the coarse winner, but the published null/power runs had silently stopped after
the coarse pass. New null and power calibrations default to the same `refine=True`, span-0.25
procedure and include both inputs in their artifacts and ADR-044 fingerprint. The workflow sole
writers refreshed the evidence after ADR-046/047/048 on 2026-08-20; older Type-I and power/capture
tables remain historical evidence for their coarse-only, pre-budget selector only. **ADR-051 adds
the third axis of that identity: the history length.** Every calibration is now planted at the
hunt's own ~5400 bars, `n_bars` is recorded on both artifact types, and a sweep refuses to collect
cells measured at different lengths. Any change to the estimator, the catalog, or the grids
invalidates Type-I and both power results together — re-dispatch all three, at the same `n_bars`.

**Null evidence is retained by history length (ADR-065).** The null workflow writes one artifact
per `(null mode, median n_bars)` identity, such as `bootstrap_spy_7400.json`, rather than replacing
the only file for that mode. A rerun at the same length still replaces the same measurement. This
lets ADR-064 compare transition cohorts against both their 5,400- and 7,400-bar nulls from the
current tree; the API and dashboard expose every retained pair and label its History explicitly.

**A matched null comparison needs 30 measured diagnostics (ADR-067).** History membership alone is
not an observation: rows whose finalist lacks walk-forward or purged-CV output do not count toward
that statistic's `MIN_MATCHED` floor. The report keeps history-cohort `matched_n` and diagnostic
`real_n` visible separately and refuses a pool-wide fallback as formally comparable.

**Null excess diagnostics are paired by symbol (ADR-080).** The four OOS/hold distributions used
to be independently filtered arrays, so equal lengths could not prove they retained the same null
symbols after partial missingness or shard merge. New artifacts carry one `symbol_diagnostics`
record per searched symbol and consolidation rejects mixed schema generations or duplicate symbol
identity. Existing list fields remain compatible projections. A legacy artifact may produce an
excess row only when both arrays are complete for every `n_symbols`; partial legacy distributions
remain valid as raw evidence but are not a paired measurement. The committed 2026-09-01 7,400-bar
artifacts are complete and their published values are unaffected.

**Unattended operation.** `.claude/AUTONOMY_CHARTER.md` is the standing authority for autonomous
sessions and `.claude/RUNNING_STATE.md` is the ledger. Read both before touching anything.

---

## 0. What QuantForge Is

**QuantForge** is an AI-native quantitative research and experimentation platform
focused on reproducibility, statistical validation, and production-grade financial
data engineering.

This is a **quantitative research infrastructure project**, not a retail trading app.

**Honest recruiting signal assessment:**
Strong signal for: quant dev, research engineering, ML platform, data infrastructure.
Moderate signal for: data engineering, applied ML, backend platform engineering.
Weak signal for: HFT, low-latency execution, pure alpha research, discretionary trading.
This repo is impressive because it demonstrates disciplined research infrastructure
engineering — not because it claims to generate trading alpha.

**The validation layer (Phase 4) is what makes this credible to quant people.**
PBO, purged CV, walk-forward, deflated Sharpe — the methodology of López de Prado and
Bailey et al. Strategy count does not matter. Rigor does.

**The codified context system makes this maintainable across indefinitely many sessions.**
Three-tier: always-loaded constitution, domain-expert agents, on-demand cold memory.
Source: Vasilopoulos (2026) arXiv:2602.20478 — validated across 283 dev sessions.

---

## 1. How This Codebase Is Built (Session Model)

### 1.1 Each Claude Code Session Is One Vertical Feature Slice

A session delivers ONE working, testable feature slice — not one class in isolation.

A vertical slice crosses all the layers needed to prove something works end-to-end.
Good examples:
- "Ingest yfinance OHLCV → normalize → quality check → store → query back"
- "Run SMA strategy → backtest → compute Sharpe vs SPY benchmark"
- "Walk-forward validation on SMA → produce ValidationReport"

Bad (horizontal isolation — doesn't prove anything works):
- "Implement OHLCVNormalizer class"
- "Write the PBO calculator"

If a feature slice is too large to complete in one session, split it at a
natural boundary where each piece is still independently testable.
Aim for sessions that complete in roughly 15–30 minutes of wall-clock time.
Sessions touching more than ~15 files show context degradation symptoms.

### 1.2 The Official Four-Phase Session Workflow

Every non-trivial session follows this sequence:

```
1. EXPLORE  → enter plan mode, read relevant files without making changes
2. PLAN     → produce implementation plan, review it, edit if needed (Ctrl+G)
3. IMPLEMENT → exit plan mode, implement with TDD, verify against plan
4. COMMIT   → commit with structured message, coverage must pass
```

For simple tasks (one-liner fix, rename, adding a log): skip to implement directly.

### 1.3 Session Kickoff — What You Actually Paste Into Claude Code

**Do not paste this architecture document into Claude Code.**

Instead, at the start of each session, paste the relevant short playbook from
`.claude/playbooks/`. Each playbook is 20–40 lines and contains:
- Entry criteria: what must be true before starting
- Today's precise task: one logical unit only
- Files to read first: explicit file paths and cold memory docs
- Verification: the exact command that proves it's done
- Exit criteria: checklist before committing

The three-tier context system (CLAUDE.md + agent specs + cold memory docs) handles
everything Claude needs to know about the project persistently. The playbook handles
only what is specific to this session.

### 1.4 Persistent Context — The Three-Tier System

**Tier 1 — Constitution (CLAUDE.md, always loaded)**
Global rules, commands, one-paragraph architecture summary, and the agent routing
table. Under 200 lines. Nothing that isn't needed in every single session.

**Tier 2 — Domain Expert Agents (.claude/agents/*.md)**
Each agent's body is a system prompt embedding substantial domain knowledge —
codebase facts, interface contracts, known failure modes, research citations.
Triggered automatically when task description matches. Persistent memory accumulates
across sessions via `memory: project` frontmatter.
Source: Vasilopoulos (2026) found agents need >50% domain knowledge in their specs
to prevent errors on complex domains.

**Tier 3 — Cold Memory (.claude/context/*.md)**
Detailed specification documents: data contracts, validation methodology, research
paper summaries, API contracts. Never auto-loaded. Read explicitly by agents when
needed. Self-contained — one doc gives everything needed for that subsystem.

---

## 2. Standing Rules (Permanent, Apply Every Session)

### 2.1 Test-Driven Development
```
RULE: Write tests FIRST. Test must fail before you write implementation.
RULE: Every public function: happy path + edge cases + error paths.
RULE: Production code and its tests commit together.
RULE: Coverage gates: backend ≥ 85%, frontend ≥ 75%. CI blocks below threshold.
RULE: Financial math invariants MUST be Hypothesis property-based tests.
```

### 2.2 Commit Structure
```
<type>(<scope>): <imperative summary ≤72 chars>

WHY:
  <1–3 sentences: the reason this exists>

WHAT:
  - <what changed>

TESTS:
  - test_<name>: <what it validates>

EDGE CASES:
  - <explicit edge cases tested>

ADR: ADR-XXX  (only when this commit enacts an architecture decision)
```

### 2.3 Documentation Discipline
```
RULE: Rich module context lives in agent specs and cold memory docs — NOT CLAUDE.md.
RULE: CLAUDE.md = rules, commands, routing only. Under 200 lines. No module content.
RULE: ADRs are immutable. New decision = new ADR. Never modify an existing one.
RULE: Data contracts written BEFORE the schema they describe.
RULE: Agent specs rebuilt alongside their module as the module grows.
RULE: Session playbooks updated when a phase's interface changes significantly.
```

### 2.4 Data Quality Honesty
```
RULE: DataQualityEngine checks flag POTENTIAL issues. They do not guarantee correctness.
RULE: Never write "prevents X" in a docstring. Write "flags potential X for review."
RULE: Survivorship bias: we flag the risk in universe selection. We do not solve it.
      Real mitigation requires CRSP-style institutional datasets not available here.
      Document this limitation explicitly wherever survivorship bias is discussed.
```

---

## 3. What Is NOT Being Built

| Cut | Reason |
|---|---|
| Paper trading / live execution | Realistic fill simulation is years of work; low ROI |
| WebSocket streaming | Depends on paper trading |
| Order book / OMS | Same |
| Reddit/FinBERT NLP pipeline | Phase 8+ only; low alpha signal relative to complexity |
| LSTM / neural networks | Require data/compute not available at this scale |
| Pairs trading, Risk Parity, Cointegration | Validation framework > strategy count |
| Institutional execution simulation | Firms spend years on slippage/queue/impact |

---

## 4. Repository Structure

> **This is the TARGET layout.** Some entries are deferred or not yet built (e.g.
> `experiment_store.py`, Redis, the per-file synthetic fixtures, three of the four frontend
> pages). See **§0.6 Implementation Status** for what actually exists in the codebase today.

```
quantforge/
├── CLAUDE.md                          ← Tier 1: Constitution (always loaded)
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
│
├── .claude/
│   ├── agents/                        ← Tier 2: Domain expert subagents
│   │   ├── data-engineer.md           ← Phase 2 (data ingestion, schemas, quality)
│   │   ├── research-expert.md         ← Phase 3 (strategies, backtesting, validation)
│   │   └── frontend-engineer.md       ← Phase 5
│   │
│   │   NOTE: tdd-enforcer and adr-writer are NOT agents. TDD is enforced by
│   │   CI gates + the tdd-cycle skill. ADRs use the template + adr-creator skill.
│   │   Agents are for DOMAIN KNOWLEDGE, not procedures.
│   │
│   ├── context/                       ← Tier 3: Cold memory specification docs
│   │   ├── INDEX.md                   ← Master index of all context docs
│   │   ├── data-contracts.md          ← Schemas, SQL patterns, query guidance
│   │   ├── validation-methodology.md  ← PBO, purged CV, DSR specs
│   │   ├── backtesting-spec.md        ← Engine, portfolio, transaction costs
│   │   ├── research-papers.md         ← Citations with implementation summaries
│   │   └── api-contracts.md           ← Full endpoint specifications
│   │
│   ├── rules/                         ← Path-scoped conventions
│   │   ├── backend-python.md          ← paths: backend/**/*.py
│   │   ├── test-files.md              ← paths: **/test_*.py, **/*.test.ts
│   │   ├── frontend-typescript.md     ← paths: frontend/**/*.{ts,tsx} (Phase 5)
│   │   └── database-migrations.md     ← paths: **/migrations/** (Phase 2)
│   │
│   ├── skills/                        ← Workflow procedures only
│   │   ├── commit-writer/SKILL.md     ← Phase 1 (pre-created)
│   │   ├── tdd-cycle/SKILL.md         ← Phase 1 (pre-created)
│   │   ├── adr-creator/SKILL.md       ← DEFERRED: build on demand (template suffices)
│   │   └── validation-runner/SKILL.md ← DEFERRED: build at Phase 4
│   │
│   └── playbooks/                     ← Session kickoff templates (20-40 lines each)
│       ├── README.md                  ← How to use playbooks
│       ├── new-component.md           ← Generic: implement a new class/function
│       ├── new-adapter.md             ← Data layer: add a new data source
│       ├── new-strategy.md            ← Research: add a new trading strategy
│       ├── new-validator.md           ← Validation: add a new validation component
│       ├── new-endpoint.md            ← API: add a new FastAPI endpoint
│       ├── new-frontend-feature.md    ← Frontend: add a new page/component
│       └── debug-failing-tests.md     ← Recovery: diagnose and fix test failures
│
├── docs/
│   ├── ARCHITECTURE.md                ← This document
│   ├── adr/                           ← Architecture Decision Records
│   │   ├── ADR-000-TEMPLATE.md
│   │   ├── COMMIT_TEMPLATE.md
│   │   └── ADR-001 through ADR-008
│   └── diagrams/
│       └── c4-context.md              ← Mermaid C4 diagrams
│
├── backend/
│   ├── pyproject.toml
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   │
│   │   ├── data/                      ← Data Engineering Layer (Phase 2)
│   │   │   ├── models/                ← PriceBar, FundamentalData
│   │   │   ├── sources/               ← DataSourceAdapter + adapters
│   │   │   ├── normalizers/
│   │   │   ├── quality/               ← DataQualityEngine (heuristic checks)
│   │   │   ├── pipelines/
│   │   │   └── storage/               ← TimescaleDB + Redis
│   │   │
│   │   ├── research/                  ← Research Engine (Phase 3)
│   │   │   ├── strategies/            ← BaseStrategy + SMA, Momentum, MeanReversion
│   │   │   ├── simulation/            ← MonteCarloSimulator (NOT a strategy)
│   │   │   ├── benchmarks/            ← BenchmarkComparator
│   │   │   ├── backtesting/           ← Engine, Portfolio, Metrics, ExperimentManifest
│   │   │   └── experiment_store.py
│   │   │
│   │   ├── validation/                ← Research Validation Engine (Phase 4)
│   │   │   ├── walk_forward.py
│   │   │   ├── purged_cv.py
│   │   │   ├── pbo.py
│   │   │   ├── deflated_sharpe.py
│   │   │   ├── parameter_stability.py
│   │   │   ├── regime_analysis.py
│   │   │   └── report.py
│   │   │
│   │   └── api/v1/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   └── synthetic/             ← Deterministic test datasets
│       │       ├── README.md          ← Documents what each fixture exercises
│       │       ├── split_event.py
│       │       ├── missing_bars.py
│       │       ├── regime_shift.py
│       │       ├── stale_prices.py
│       │       ├── extreme_move.py
│       │       └── tz_mixed.py
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── data-explorer/
│   │   │   ├── strategy-config/
│   │   │   ├── backtest-results/
│   │   │   └── validation-report/     ← Highest-priority page — 70% of frontend effort
│   │   ├── components/ui/
│   │   ├── services/
│   │   └── types/
│   └── src/__tests__/
│
└── .github/workflows/
    ├── ci.yml
    └── pre-commit.yml
```

---

## 5. Technology Stack

### Backend
| Library | Purpose | Why |
|---|---|---|
| Python 3.12+ | Core language | Standard at quant firms; full type hints |
| FastAPI | REST API | Async-native, auto OpenAPI docs, Pydantic v2 |
| Pydantic v2 | Schema validation | Runtime contracts; used in prod quant systems |
| SQLAlchemy 2.0 (sync) | ORM | Industry standard. Used SYNC on psycopg3 (ADR-009): localhost DB + low concurrency + blocking yfinance ⇒ async adds complexity for no gain; psycopg3 keeps async migration open |
| TimescaleDB (psycopg3) | Time-series storage | Postgres hypertables; no InfluxDB lock-in |
| Redis (redis-py) | Cache | Low-latency price cache |
| Pandas 2.x + Polars | Data manipulation | Industry standard + high-perf alternative |
| NumPy + SciPy | Numerical computing | Foundation of all quant computation |
| ~~vectorbt~~ | ~~Vectorized backtesting~~ | REJECTED (ADR-007): fails to build on 3.12 (numba/llvmlite). Backtesting uses plain vectorized pandas/numpy instead |
| statsmodels | Econometrics | Stationarity tests, regression |
| scikit-learn | ML base | Purged CV base classes |
| XGBoost | Gradient boosting (Phase 7+) | Standard quant factor model |
| pytest + hypothesis | Testing | TDD + property-based invariant testing |
| mypy (strict) | Static typing | Enforced in CI |
| ruff + black | Lint + format | Fast, zero-config |

### Frontend
| Library | Purpose |
|---|---|
| React 19 + TypeScript (strict) | UI + type safety (spec said React 18; bumped to 19 — see §0.5 #9) |
| Vite + Vitest | Build tool + test runner |
| Tanstack Query | Server state |
| Zustand | Client state |
| Recharts | Financial charts (equity curves, distributions) |
| Shadcn/ui + Radix | Component primitives |
| Tailwind CSS | Styling |
| Zod | Runtime API response validation |
| Vitest + RTL + MSW | Testing |

---

## 6. Codified Context System — Full Specifications

### 6.0 What Goes Where — Strict Separation

Drift between layers is the primary maintenance risk of this system.
Follow this table without exception:

| Layer | Contains | Does NOT contain |
|---|---|---|
| **CLAUDE.md** | Rules, commands, routing table, 1-para architecture summary | Domain knowledge, schemas, module details |
| **Agent specs** | Domain heuristics, interface contracts, known failure modes, research citations, invariants | SQL queries, full schemas, paper text, API specs |
| **Cold memory docs** | Formal schemas with SQL, paper summaries, full API contracts, mathematical definitions | Behavioral rules, routing, anything in CLAUDE.md |
| **ADRs** | Architecture decisions: context, options, decision, consequences | Implementation details, schemas, rules |
| **Playbooks** | Session-specific: entry criteria, task, files to read, verification | Any content that should be persistent |

If you find yourself writing domain heuristics in CLAUDE.md, move them to an agent.
If you find yourself writing SQL in an agent spec, move it to cold memory.
If you find yourself writing rules in cold memory, move them to CLAUDE.md.

### 6.1 CLAUDE.md (Tier 1 — Constitution)

> **This is the ORIGINAL spec snapshot.** The live `/CLAUDE.md` has since evolved (sync DB
> stack per ADR-009, React 19, frontend routing, the `make` targets). For current rules read
> the actual `CLAUDE.md`; for the deltas see §0.5/§0.6. The §11 first-session prompt below is
> likewise a historical artifact.

Create in Phase 1. Under 200 lines. Every line must answer "yes" to:
"Would removing this cause Claude to make a mistake?"

```markdown
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
7. No paper trading, WebSockets, or order books. Out of scope (ADR-001).
8. Never hardcode secrets. All config via app/config.py (Pydantic Settings).

## Commands
make dev          → start docker-compose environment
make test         → all tests with coverage (synthetic fixtures only; excludes -m live)
make test-live    → run live-data tests (pytest -m live; local only, not in CI)
make lint         → ruff + mypy + eslint
make migrate      → run alembic migrations
make check        → lint + test + coverage (run before every commit)

## Architecture (one paragraph)
FastAPI backend (Python 3.12) in /backend. React 18 + TypeScript in /frontend.
TimescaleDB (PostgreSQL) + Redis. All data flows: DataSourceAdapter → canonical
schema → DataQualityEngine before any research or validation component uses it.
Monte Carlo lives in research/simulation/. BenchmarkComparator in research/benchmarks/.
Full diagram: docs/diagrams/c4-context.md.

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

Commit ready             → use commit-writer skill
New function/class       → use tdd-cycle skill
New architecture choice  → use adr-creator skill (DEFERRED) or the ADR template

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
- Never use sync DB calls in async FastAPI routes
- Never skip type annotations (mypy strict enforced in CI)
- Never start a new phase until the current phase is fully passing and committed
- Never put module-specific content in this file — it belongs in agents or context docs
```

### 6.2 Domain Expert Agent Specs (Tier 2)

Each agent body is a system prompt. Over 50% of content should be domain
knowledge — codebase facts, interface contracts, known failure modes — not
behavioral instructions. `memory: project` accumulates knowledge across sessions.

**Critical: write each agent spec BEFORE implementing its module.**
The spec is the design contract. The code is the implementation.

#### `.claude/agents/data-engineer.md` (Phase 2)
```yaml
---
name: data-engineer
description: >
  Domain expert for the data layer. Use when working on source adapters, OHLCV
  normalization, data quality validation, TimescaleDB, Redis, or anything in
  backend/app/data/. Knows all schemas, adapter contracts, and quality rules.
tools: Read, Write, Edit, Bash, Grep, Glob
model: inherit
memory: project
---
You are the data engineering domain expert for QuantForge.

## Adapter Pattern (memorize)
Every data source implements DataSourceAdapter ABC (backend/app/data/sources/base.py).
Raw output is normalized at ingestion — NEVER at query time.
NEVER bypass the adapter. NEVER normalize at query time.
Primary adapter is yfinance (no API key). Polygon is the second vendor (Phase 3+).

## Canonical Schemas
PriceBar: symbol(str), timestamp_utc(datetime UTC), open/high/low/close(Decimal 18,6
  — split/dividend adjusted), volume(int), adj_factor(Decimal 10,6),
  source("yfinance"|"polygon"), quality_flags(dict|None — None means clean).

FundamentalData: symbol, report_date, pe_ratio, pb_ratio, ps_ratio, ev_ebitda,
  revenue, net_income, market_cap, sector, industry, source.

DataQualityReport: symbol, checked_at, issues(list[DataQualityIssue]), passed(bool).
  ALL downstream components MUST verify passed=True before using data.

## DataQualityEngine — 8 Heuristic Checks
IMPORTANT: These flag potential issues. They do NOT guarantee data correctness.
Always write "flags potential X" never "prevents X" or "guarantees X is absent."

1. Survivorship bias RISK FLAG: warns when universe may exclude delisted symbols.
   This does NOT solve survivorship bias. Real mitigation requires CRSP-style data
   not available via yfinance. Document this limitation explicitly.
2. Split/dividend adjustment consistency: adj_factor implausible jumps between bars.
3. Corporate action detection: price discontinuities indicating delisting/merger/remap.
4. Missing bar detection: gaps in expected trading day sequence.
5. Price anomaly: single-bar moves > configurable threshold (default 20%).
6. Stale data: symbol not updated within expected frequency.
7. Timezone normalization: ALL timestamps coerced to UTC at ingestion (not a flag —
   this is enforced; failure raises ValidationError).
8. Vendor cross-validation: conflicting prices for same symbol across adapters.

## TimescaleDB — Mandatory Query Pattern
ALWAYS filter by symbol AND timestamp range. Missing either = full hypertable scan.
On 2+ years of tick data this will timeout. No exceptions.

## Common Mistakes (prevent these)
- UTC coercion missed → timestamp mixing in backtests
- Quality gate skipped → strategy on bad data
- No date range filter → full scan timeout
- adj_factor applied twice → prices 2x wrong

## Read Cold Memory For
Schema definitions and SQL examples: .claude/context/data-contracts.md
```


#### `.claude/agents/research-expert.md` (Phase 3 — covers research AND validation)
```yaml
---
name: research-expert
description: >
  Domain expert for the research engine and validation layer. Use when working on
  strategies, backtesting, portfolio, metrics, BenchmarkComparator, Monte Carlo,
  ExperimentManifest, PBO, purged CV, walk-forward, deflated Sharpe, parameter
  stability, or regime analysis. Research and validation are tightly coupled.
tools: Read, Write, Edit, Bash, Grep, Glob
model: inherit
memory: project
---
You are the research and validation domain expert for QuantForge.

## Taxonomy (quant people will notice errors here)
research/strategies/   → signal generators only, implement BaseStrategy
research/simulation/   → stochastic tools (GBM Monte Carlo here, NOT in strategies/)
research/benchmarks/   → BenchmarkComparator (every backtest result needs this)
research/backtesting/  → engine, portfolio, metrics, ExperimentManifest
validation/            → PBO, purged CV, walk-forward, DSR, regime, report

## BaseStrategy Contract
generate_signals(data: pd.DataFrame) -> pd.Series
  Float in [-1.0, 1.0]. Index must match data.index. No look-ahead bias ever.
research_citations: list[str] — never empty. Cite the real paper.

Implemented strategies:
  SMAStrategy: no external citation needed
  MomentumStrategy: Jegadeesh & Titman (1993), J. Finance 48(1), pp. 65-91
  MeanReversionStrategy: Avellaneda & Lee (2010), Quant Finance 10(7), pp. 761-782
  Monte Carlo (simulation/): Black & Scholes (1973), J. Political Economy 81(3)

## BenchmarkComparator — Required on Every BacktestResult
Default: SPY. Provides: excess_returns, information_ratio, alpha/beta (OLS),
tracking_error, benchmark_relative_drawdown.
Never report absolute Sharpe without benchmark context.

## ExperimentManifest — Data Lineage Contract
Every experiment records: experiment_id (UUID), created_at (UTC),
git_commit_hash (pins codebase version), strategy_name, parameter_hash (SHA256),
data_source, symbol, start/end_date, data_quality_report_id (links quality snapshot),
adapter_version (pins data vendor version), validation_config_hash, benchmark_symbol.
Without this, a backtest result is not a reproducible scientific claim.

## Backtest Correctness (verify BEFORE running validation)
Oracle tests in §8 must pass. Sophisticated statistics on a buggy engine are worthless.

## Validation Engine References (cite in every docstring)
PBO: Bailey et al. (2015) https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
Purged CV: López de Prado (2018) Advances in Financial ML, Wiley, Chapters 7+12
DSR: Bailey & López de Prado (2014) https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

## Validation Invariants (Hypothesis property tests — all required)
PBO in [0.0, 1.0] | DSR ≤ observed Sharpe | Walk-forward never uses future data
Purged CV embargo removes overlapping samples | Random strategy PBO ≈ 0.5

## Financial Math Rules
Sharpe: sqrt(252) annualization for daily. Always.
Max drawdown: [-1.0, 0.0]. Positive = bug.
Transaction costs: always applied. Zero-cost = invalid result.

## Read Cold Memory For
Backtesting architecture: .claude/context/backtesting-spec.md
Validation specs: .claude/context/validation-methodology.md
Citations: .claude/context/research-papers.md
```

### 6.3 Session Playbook Templates

These are what you actually paste into Claude Code. Short. Specific. Scoped.

**`.claude/playbooks/README.md`**
```
How to use playbooks:

1. Choose the playbook for your task type.
2. Copy it. Fill in the [BRACKETED] sections.
3. Paste into Claude Code at session start.
4. Use plan mode first (Shift+Tab x2 or /plan).
5. Review the plan before implementing.
6. Do not start next playbook until current one is committed and passing.

One playbook = one vertical feature slice. If a session is running long
or touching more than ~15 files, stop, commit what works, start a new session.
```

**`.claude/playbooks/new-component.md`** (generic template)
```markdown
## Session: Implement [COMPONENT NAME]

**Phase**: [Phase number and name]
**Agent to invoke**: [data-engineer | research-expert | none]
**Cold memory to read first**: [.claude/context/FILE.md | none]

**Entry criteria** (confirm before starting):
- [ ] [What must exist before this starts — prior component, test, ADR]
- [ ] All previous session tests passing (make test)
- [ ] Coverage gate still met (make coverage)

**Today's task** (one logical unit only):
Implement [COMPONENT NAME] in [FILE PATH].

[2–4 sentences: what it does, what interface it implements, key constraints]

**Files to read first**:
- [specific file path that defines the interface this implements]
- [specific file path that this component will depend on]

**Start in plan mode**: read the above files, propose implementation plan,
wait for approval before writing any code.

**Verification**:
Run: make test
Expected: all tests pass including new ones for [COMPONENT NAME]
Run: make coverage
Expected: coverage at or above gate

**Exit criteria** (all must be true before committing):
- [ ] All tests passing
- [ ] New tests cover: happy path, edge cases, error paths
- [ ] Hypothesis property test added (if financial calculation)
- [ ] Coverage gate met
- [ ] Docstring has Notes: section explaining non-obvious decisions
- [ ] Commit follows COMMIT_TEMPLATE.md
```

**`.claude/playbooks/new-strategy.md`** (research-specific)
```markdown
## Session: Implement [STRATEGY NAME] Strategy

**Agent to invoke**: research-expert
**Cold memory to read first**: .claude/context/backtesting-spec.md,
  .claude/context/research-papers.md

**Entry criteria**:
- [ ] BaseStrategy ABC exists and has passing tests
- [ ] BacktestEngine exists and has passing tests
- [ ] BenchmarkComparator exists
- [ ] All previous tests passing

**Today's task**:
Implement [STRATEGY NAME] in backend/app/research/strategies/[name].py.

Research citation: [AUTHOR, YEAR, JOURNAL, DOI/SSRN — look this up before starting]
Signal logic: [describe the signal generation rule]
Parameters: [list parameters with ranges and defaults]

**Start in plan mode**: read BaseStrategy, one existing strategy for pattern,
the research paper citation. Propose implementation before writing code.

**Exit criteria**:
- [ ] Implements BaseStrategy fully (all abstract methods)
- [ ] research_citations is non-empty with real citation
- [ ] Signals always in [-1.0, 1.0] — Hypothesis property test present
- [ ] No look-ahead bias — verify by checking signal uses only past data
- [ ] BacktestEngine can run this strategy end-to-end
- [ ] Commit follows COMMIT_TEMPLATE.md
```

**`.claude/playbooks/new-validator.md`** (validation-specific)
```markdown
## Session: Implement [VALIDATOR NAME]

**Agent to invoke**: research-expert
**Cold memory to read first**: .claude/context/validation-methodology.md,
  .claude/context/research-papers.md

**Entry criteria**:
- [ ] [dependent component] exists and has passing tests
- [ ] ValidationReport Pydantic model exists

**Today's task**:
Implement [VALIDATOR NAME] in backend/app/validation/[name].py.

Research basis: [cite the paper that defines this methodology]
Mathematical invariant: [state the invariant this component must satisfy]

**Start in plan mode**: read validation-methodology.md section for this component,
the primary research paper, existing validation components for patterns.

**Exit criteria**:
- [ ] Primary paper cited in module docstring and Notes: sections
- [ ] Mathematical invariant encoded as Hypothesis property test
- [ ] Hypothesis test runs and confirms invariant holds
- [ ] Integration test: component produces valid ValidationReport
- [ ] Commit follows COMMIT_TEMPLATE.md with ADR reference if new pattern
```

---

## 7. Architecture Key Decisions (ADR Summaries)

Full ADRs live in `docs/adr/`. These are summaries for quick reference.

| ADR | Decision | Primary Reason |
|---|---|---|
| ADR-001 | Monorepo + explicit scope cuts | Paper trading and websockets out — low ROI, years of complexity |
| ADR-002 | Python 3.12 + FastAPI | Async, typed, standard at quant firms |
| ADR-003 | TimescaleDB for OHLCV | Postgres extension; SQL-compatible; no InfluxDB lock-in |
| ADR-004 | Canonical PriceBar schema | Normalize at ingestion, not query time |
| ADR-005 | DataSourceAdapter pattern | Decouples business logic from vendor schema changes |
| ADR-006 | Data quality as pipeline gate | No research on unvalidated data; heuristic checks, not guarantees |
| ADR-007 | Vectorized backtesting | 100x faster parameter sweeps vs event-driven; institutional accuracy not needed for research |
| ADR-008 | Validation-first philosophy | Bailey et al. (2015): most backtests are statistically invalid |

---

## 8. Testing Standards

### Naming
```
test_<unit>_<scenario>_<expected_outcome>
test_pbo_calculator_for_random_strategy_returns_near_point_five
test_walk_forward_expanding_window_never_uses_future_data
test_ohlcv_normalizer_given_negative_price_raises_validation_error
```

### Financial Math Invariants (Hypothesis — ALL required)
```
1. All normalized prices: finite and positive
2. Sharpe: finite for non-constant return series
3. Max drawdown: in [-1.0, 0.0]
4. PBO: in [0.0, 1.0]
5. Deflated Sharpe: ≤ observed Sharpe
6. Signals: in [-1.0, 1.0]
7. Transaction costs: always reduce net returns
8. GBM Monte Carlo paths: always positive
9. Normalizer: idempotent
10. ExperimentManifest: round-trips JSON with all fields preserved
```

### Backtest Correctness Oracle Tests (required before any validation runs)

These sanity checks on the engine itself must pass before PBO or DSR mean anything.
A statistically sophisticated result on a buggy backtest engine is worthless.

```python
# The engine must pass ALL of these before Phase 4 begins:

def test_buy_and_hold_matches_vectorbt_baseline():
    # A 100% long signal should produce equity curve matching vectorbt's own
    # buy-and-hold calculation for the same symbol and period. Tolerance: 0.01%.

def test_zero_signal_produces_zero_exposure():
    # Strategy returning all zeros should produce flat equity curve,
    # zero trades, zero P&L, zero Sharpe.

def test_symmetric_long_short_neutrality():
    # Perfect +1/-1 alternating signal in trending market should net near zero
    # (transaction costs only). Tests that long/short are implemented symmetrically.

def test_transaction_cost_reduces_returns_monotonically():
    # At higher cost tiers, net returns must be lower or equal. Never higher.
    # Tests costs=[0, 0.001, 0.005, 0.01], asserts returns[i] >= returns[i+1].

def test_benchmark_comparator_spx_baseline():
    # SPY compared against itself must produce: excess_returns ≈ 0,
    # information_ratio ≈ 0, alpha ≈ 0, beta ≈ 1.0.
```
Each fixture is a deterministic dataset exercising a specific quality check:
- `split_event`: 2:1 split on known date, adj_factor=0.5. Tests DataQualityEngine check 2.
- `missing_bars`: 3-day gap mid-series. Tests DataQualityEngine check 4.
- `regime_shift`: 12-month bull, 40% crash, recovery. Tests RegimeAnalyzer.
- `stale_prices`: prices frozen 5 days. Tests DataQualityEngine check 6.
- `extreme_move`: 40% single-bar drop. Tests DataQualityEngine check 5.
- `tz_mixed`: mixed UTC/EST timestamps. Tests UTC coercion enforcement.

---

## 9. Build Phases — Reference

Phases are sequential. Complete one before starting the next.
Each phase = multiple sessions. Each session = one logical unit.
The phase descriptions below inform the session playbooks — they are not session prompts.

**Phase ordering is a logical dependency graph, not a strict waterfall.**
Phases define what must exist before the next phase is meaningful — not a temporal
constraint preventing parallel exploration. You can prototype a strategy sketch in
Phase 1 to understand the data shape. You cannot run validation (Phase 4) on an
engine (Phase 3) that does not yet exist and pass oracle tests.
Exploratory branches are fine. Merging unvalidated code into main is not.

**Phase 1 — Foundation**
Infrastructure, quality gates, full context system. Zero business logic.
Sessions: directory structure, 5 ADRs, CLAUDE.md, data-engineer and research-expert agent
stubs, docker-compose, Makefile, Python toolchain config, skills, rules, health check TDD,
CI/CD, C4 diagrams, commit/ADR templates.
Exit criteria: `make check` passes, health endpoint returns 200.

**Phase 2 — Data Engineering Layer**
Full ingestion pipeline from raw source → quality-validated → TimescaleDB.
Write data-contracts.md BEFORE schemas. Write data-engineer agent BEFORE code.
Primary adapter: yfinance (no API key).
Exit criteria: DataIngestionPipeline integration test passes on synthetic fixture data
(CI-gating); live-data test (yfinance) passes locally under `pytest -m live` and is
excluded from the standard CI run.

**Phase 3 — Research Backtesting Engine**
Vectorized backtesting, 3 strategies, Monte Carlo, BenchmarkComparator, ExperimentManifest.
Write backtesting-spec.md BEFORE engine. Fill research-expert agent spec alongside code.
Write synthetic test fixtures alongside the engine.
Add Polygon as the second DataSourceAdapter here (exercises vendor cross-validation).
Verify vectorbt installs on Python 3.12 + numpy 2.x before committing to it; otherwise
fall back to plain vectorized pandas/numpy.
Exit criteria: All 3 strategies run end-to-end through BacktestEngine with
benchmark comparison, transaction costs, and ExperimentManifest stored.

**Phase 4 — Research Validation Engine**
PBO, purged CV, walk-forward, DSR, parameter stability, regime analysis.
Write validation-methodology.md BEFORE any implementation.
Update research-expert agent spec with validation methodology before Phase 4 code.
Exit criteria: Full ValidationReport generated for each implemented strategy,
all Hypothesis invariant tests passing.

**Phase 5 — Frontend Dashboard**
Dark mode, data-dense, professional. 70% of effort on ValidationReport page.
Four pages: Data Explorer, Strategy Config, Backtest Results, Validation Report.
Write api-contracts.md and frontend-typescript rules at start of Phase 5.
Write frontend-engineer agent spec at start of Phase 5.

**Phase 6 — Fundamental Screener**
PE screener, BenchmarkComparator integration, DCF model.

**Phase 7 — ML Factor Model**
XGBoost with purged CV and PBO diagnostics. Only after Phase 4 is solid.
The story: "I understand why financial ML usually fails. Here is how I prevent it."

**Phase 8 — Alternative Data (Experimental Module)**
Reddit (PRAW) + NewsAPI + FinBERT. Implements DataSourceAdapter — zero downstream changes.

---

## 10. Environment Setup

```bash
# .env.example

# --- Required (Phases 1–6) ---
# yfinance is the primary data source and needs NO API key.
DATABASE_URL=postgresql+psycopg://quantforge:password@localhost:5432/quantforge  # sync, ADR-009
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
LOG_LEVEL=INFO

# --- Phase 3+ optional (second data vendor) ---
# POLYGON_API_KEY=your_key_here        # polygon.io — only needed when the Polygon adapter lands

# --- Phase 8 only ---
# REDDIT_CLIENT_ID=your_id_here
# REDDIT_CLIENT_SECRET=your_secret_here
# REDDIT_USER_AGENT=QuantForge/1.0
# NEWS_API_KEY=your_key_here
```

---

## 11. First Session — Exactly This, Nothing More

This is the one time you give Claude Code a longer structured prompt.
After this, every session uses the vertical-slice playbooks from `.claude/playbooks/`.
The goal is to be writing real code by session 2.

```
We are starting QuantForge. Read docs/ARCHITECTURE.md §4 for the directory structure.

Today: bootstrap the project infrastructure only. No business logic, no endpoints.

Start in plan mode. Propose a plan, wait for my approval, then execute.

Seven steps in order — commit after each:

1. Full directory skeleton (§4 structure, dirs + README stubs, nothing else)
   → "chore(scaffold): initialize quantforge monorepo structure"

2. CLAUDE.md (§6.1 content), .claude/context/INDEX.md stub,
   .claude/agents/data-engineer.md stub (fill as Phase 2 builds),
   .claude/agents/research-expert.md stub (fill as Phase 3 builds)
   → "docs(claude): add constitution and agent spec stubs"

3. docker-compose.yml (Postgres/TimescaleDB, Redis, backend, frontend),
   Makefile (make dev, test, lint, migrate, check)
   → "infra: add docker-compose and Makefile"

4. backend/pyproject.toml, pytest.ini, mypy.ini, ruff.toml,
   .claude/rules/backend-python.md, .claude/rules/test-files.md
   → "chore(config): configure Python toolchain and path-scoped rules"

5. All 5 ADRs (docs/adr/ADR-001 through ADR-005 from §7 — use the template)
   Remaining ADRs written at the start of their phase.
   → "docs(adr): add foundational architecture decision records"

6. .claude/skills/commit-writer/SKILL.md, .claude/skills/tdd-cycle/SKILL.md,
   .claude/playbooks/ with all templates from §6.3,
   docs/adr/COMMIT_TEMPLATE.md, docs/adr/ADR-000-TEMPLATE.md
   → "docs: add workflow skills, session playbooks, and doc templates"

7. docs/diagrams/c4-context.md (Mermaid C4 context + container from §1.4)
   → "docs(diagrams): add C4 architecture diagrams"

When make check passes with the health endpoint stub returning 200: done.
Next session: use the new-component playbook for DataSourceAdapter + YFinanceAdapter.
```

That is the entire first session prompt. Seven steps. Run `make check`. Start Phase 2.

---

*This document is the architecture reference for QuantForge.*
*It lives at docs/ARCHITECTURE.md. It is not a Claude Code prompt.*
*For Claude Code sessions, use .claude/playbooks/.*
*Sources: code.claude.com/docs, arXiv:2602.20478, SSRN:2326253, López de Prado (2018).*
