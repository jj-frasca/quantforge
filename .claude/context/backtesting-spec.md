# Backtesting Spec (Cold Memory)

Formal contracts for the research engine (Phase 3). Read when working on
`backend/app/research/`. Decisions: ADR-007 (vectorized pandas/numpy, NOT vectorbt).
Behavioral rules live in CLAUDE.md; this holds shapes, formulas, and the oracle tests.

---

## 1. Price frame convention

Strategies and the engine operate on a pandas DataFrame, not raw PriceBars:

- **Index**: tz-aware UTC `DatetimeIndex`, ascending, unique.
- **Columns**: at least `close` (float). May include `open`/`high`/`low`/`volume`.
- Built from `list[PriceBar]` via `bars_to_frame(bars)` (uses adjusted `close`, as `float`).

`float` is used inside the engine (vectorized numpy math); `Decimal` is the storage/contract
type (PriceBar). The conversion happens once at `bars_to_frame`.

ADR-157 hardens each canonical `PriceBar` before that conversion: optional `quality_flags` are
defensive finite-JSON copies, and both repositories revalidate an entire incoming batch before any
state or transaction access. Unchecked model copies therefore cannot inject invalid OHLC/identity
or partially overwrite cached evidence; frame construction and adjustment semantics are unchanged.

---

## 2. BaseStrategy contract

`app/research/strategies/base.py`. ABC:

- `generate_signals(data: pd.DataFrame) -> pd.Series`
  - returns a float position weight per bar, **in [-1.0, 1.0]** (−1 short … 0 flat … +1 long).
  - index MUST equal `data.index`.
  - **No look-ahead**: signal at time *t* may use only data up to and including *t*.
- `research_citations: list[str]` — non-empty; cite the real paper.
- `name: str`, `parameters: dict` (for the manifest's parameter hash).

### Strategy catalog (ADR-010)
The authoritative list of strategies lives in `app/research/strategies/catalog.py` and is
served to the frontend via `GET /api/v1/strategies`. **Don't maintain a copy here** — the
list drifts. The catalog carries each strategy's UI label, description, citations, and
parameter schema; the frontend renders the form generically from it.

Adding a strategy is a 5-line backend-only change (subclass + Pydantic config + dispatch +
catalog entry + consistency-test map). See ADR-010 "Pattern for adding a strategy". The
consistency test (`tests/unit/test_strategy_catalog_consistency.py`) is load-bearing: it
guarantees catalog ↔ Pydantic field-name parity and that every catalog default round-trips
through API validation.

---

## 3. BacktestEngine (vectorized, ADR-007)

**Why hand-rolled, not a library (2026 landscape — don't relitigate without new info):**
The engine is intentionally a ~50-line pure pandas/numpy kernel, guarded by the §8 oracle tests.
The library options were researched and rejected for *this* project:
- **vectorbt (OSS)** — fails to build on Python 3.12 (numba → llvmlite native build); OSS is
  effectively frozen behind the paid **vectorbt PRO** (closed-source, $20/mo) — unusable in a
  public portfolio repo a reviewer must clone and run.
- **backtrader** — active development stopped ~2018; 3.10+ friction; event-driven realism we
  explicitly don't need (ADR-001).
- **zipline-reloaded** — heavy, data-bundle ceremony, US-equity/factor oriented; overkill.
- **backtesting.py** — maintained + lightweight but **single-asset**; doesn't fit the
  `(T × N)` multi-config returns matrix that PBO/CSCV needs. (Possible *dev-only cross-check*, not the core.)
- **NautilusTrader** — execution-realism/live-parity focus; out of scope (ADR-001).
There is no maintained, free, OSS, 3.12-friendly *vectorized-sweep* library that fits — and
hand-rolling the correct math (look-ahead avoided, cost-on-turnover) is on-thesis for a project
whose whole signal is methodological rigor. Revisit only if sweeps hit 10^5–10^6 combos
(numpy-broadcast first; vectorbt PRO as a private research-only tool, never in the public repo).

`app/research/backtesting/engine.py`. Pure pandas/numpy. Given `prices` (close series) and
`signals` (position weights), `initial_capital`, and `cost_rate` (fraction per unit turnover):

```
returns      = prices.pct_change().fillna(0)
position     = signals.reindex(prices.index).clip(-1, 1).fillna(0)
# trade on the NEXT bar -> no look-ahead: yesterday's position earns today's return
gross        = position.shift(1).fillna(0) * returns
turnover     = position.diff().abs().fillna(position.abs())   # |Δposition| each bar
costs        = turnover * cost_rate
net          = gross - costs
equity_curve = (1 + net).cumprod() * initial_capital
```

`BacktestResult` (frozen): `equity_curve` (Series), `returns` (net Series), `metrics`
(`BacktestMetrics`), `n_trades` (count of nonzero turnover bars), `cost_rate`, `position`
(the clipped/filled position Series — exposed so API callers, e.g. `/backtest`'s
`trade_markers`, can derive signal-change events without re-running the strategy).

**Invariants** (Hypothesis): equity_curve all finite & > 0 for finite inputs; zero signal →
flat equity, zero trades; higher cost_rate → total return monotonically ≤.

---

## 4. Metrics

`app/research/backtesting/metrics.py` — `BacktestMetrics` (frozen):

- `sharpe`: `sqrt(252) * mean(net) / std(net)` (daily). 0.0 if std==0 (constant returns).
- `max_drawdown`: `min(equity/equity.cummax() - 1)` — **in [-1.0, 0.0]**. Positive = bug.
- `total_return` (ADR-110): `product(1 + net) - 1` over every net observation, including the
  first bar's initial-position cost. It is never derived from `equity[-1]/equity[0]`, because the
  first equity observation is already post-return and would drop that first period.
- `annualized_return` (ADR-110): the geometric compound rate
  `product(1 + net) ** (252 / n) - 1`; it therefore always has the same sign as total return.
  Non-finite returns or a non-positive compounded-wealth path fail closed instead of emitting a
  misleading scalar. `annualized_vol` retains standard sqrt(252) scaling.
- `sortino` (ADR-107): `sqrt(252) * mean(net) / downside_semi_std(net)` — same sqrt(252)
  convention as Sharpe, but the denominator only squares shortfall below target 0.0 (upside
  dispersion never penalizes) and divides by the full sample size. 0.0 if no return falls below
  target, mirroring Sharpe's degenerate-series convention rather than +inf. **Descriptive only —
  not read by the gate, PBO, DSR, or any threshold** (charter §4).
- `calmar` (ADR-108, corrected by ADR-110): geometric `annualized_return / abs(max_drawdown)` — a pure ratio of two other
  `BacktestMetrics` fields, not a new estimate from the returns Series. 0.0 if `max_drawdown ==
  0.0`, same degenerate-series convention. **Descriptive only**, same as `sortino` above.
- `sharpe_ci` (ADRs 109, 111): `SharpeConfidenceInterval | None` — a 95%-default iid-normal confidence interval on
  `sharpe` via Lo (2002)'s asymptotic standard error, `sqrt((1 + SR^2/504) / years)` where `years =
  len(returns) / 252`. A DIFFERENT question than PBO/DSR (selection bias across a search): this is
  the sampling uncertainty in one already-observed Sharpe. `None` below 2 returns or below 1 year
  of data (the asymptotic normal approximation is unreliable there) — callers must handle null.
  Re-derives the same formula `app/research/lab/frontier.py`'s `sharpe_standard_error` (ADR-043)
  uses rather than importing it: `backtesting/` sits below `lab/` in this codebase's layering.
  The interval carries `assumption: "iid_normal"`; serial correlation or non-normal returns can
  make it too narrow. `confidence` must be finite and strictly between 0 and 1. **Descriptive
  only.** Rendered in `BacktestResultView` as an `IID-normal 95% interval: lower – upper` line
  under the Sharpe tile when present, nothing when `null`.

---

## 5. BenchmarkComparator

`app/research/benchmarks/comparator.py`. Default benchmark SPY. Given strategy `net` returns
and `benchmark` returns (aligned), requires at least two finite overlapping observations and each
return greater than -1 (ADR-112):

- `excess_returns = strat - bench`
- `information_ratio = sqrt(252) * mean(excess) / std(excess)`
- `beta = cov(strat, bench) / var(bench)`; `alpha = mean(strat) - beta*mean(bench)` (annualized)
- `tracking_error = sqrt(252) * std(excess)`
- `benchmark_relative_drawdown`: max drawdown of the **relative** equity curve
  `(1+strat).cumprod() / (1+bench).cumprod()` from a prepended unit baseline (a ratio — always
  positive). Do NOT compound the
  return *difference* (`strat - bench`); it can fall ≤ −1 and produce a meaningless curve.

**Oracle**: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.0 (ARCHITECTURE.md §8).
Never report an absolute Sharpe without benchmark context.

---

## 6. Monte Carlo (simulation/, NOT a strategy)

`app/research/simulation/monte_carlo.py`. GBM: `S_{t+1} = S_t * exp((mu - 0.5 sigma^2) dt +
sigma sqrt(dt) Z)`. Seeded RNG for determinism. **Invariant**: all path values > 0
(ARCHITECTURE.md §8 #8). Cite Black & Scholes (1973).

---

## 7. ExperimentManifest (lineage)

`app/research/backtesting/manifest.py`. Frozen, JSON round-trips with ALL fields preserved
(§8 #10): `experiment_id` (UUID), `created_at` (UTC), `git_commit_hash`, `strategy_name`,
`parameter_hash` (SHA256 of sorted params), `data_source`, `symbol`, `start_date`, `end_date`,
`data_quality_report_id`, `adapter_version`, `validation_config_hash`, `benchmark_symbol`.
Without it, a backtest result is not a reproducible scientific claim.

ADR-137 makes this a production contract for new single-name StrategyLab rows rather than a model
used only by tests. A real-data hunt accepts a `ResearchDataset` only after `DataQualityEngine`
passes its exact vendor bars, then stores both that full report and a manifest for the selected
trial. The manifest shares the pool row's experiment UUID and links the embedded report UUID;
symbol, source, adapter version, request dates, code revision, selected parameter hash, and gate
configuration are fixed before the row is written. Legacy and synthetic rows remain explicitly
nullable because their vendor quality lineage cannot be reconstructed honestly.

ADR-138 uses a distinct `CrossSectionalManifest` for a multi-symbol claim. Shared fields bind the
experiment, selected strategy/parameter hash, validation config, executed revision, and equal-weight
universe benchmark. Its ordered `PanelComponentManifest` list binds each retained panel column to
one passed report UUID, source, adapter version, and requested range. The experiment embeds those
complete reports and validates that their ordered symbols exactly equal `universe_symbols`.

ADR-163 makes both manifest shapes authoritative before outer-experiment attachment. Creation is
timezone-aware UTC; Git and SHA-256 identities are full lowercase hexadecimal values; shared
identity is non-empty; symbols are normalized; acquisition ranges are ordered; and panel components
are defensively reconstructed into an immutable JSON-array-compatible list. Outer selected-trial and
quality-report links remain unchanged, as do acquisition and methodology.

ADR-139 extends the same real-data boundary to single-name forward testing. `manage_portfolio` and
paper target sizing require `ResearchDataset`, not a plain frame. Every newly computed
`ForwardScore` stores its `ResearchDatasetEvidence` (complete report, source, adapter version,
request range, and executed revision), and its report symbol must match the frozen position.
Provider/quality failures leave the prior managed score unchanged and yield no broker target;
legacy scores without evidence remain valid.

ADR-164 makes `ResearchDatasetEvidence` revalidate instantiated inputs, including unchecked copies,
before direct validation or attachment to either forward-score model. Acquisition bounds must be
timezone-aware and normalize to UTC. `ResearchDataset` shares this identity boundary and retains
the validated report snapshot before its frame checks. Existing JSON shapes, quality rules, and
legacy absent evidence remain unchanged; mutable frame ownership and outer-score copies are
separate audit surfaces.

ADR-140 applies panel semantics to cross-sectional forward testing. The managed-book provider must
return one `ResearchDataset` per frozen universe symbol; exact membership, report symbols, common
revision, and post-alignment columns are checked before the factor or equal-weight benchmark is
computed. Any failure defers the entire position update instead of scoring a different subset.
New `CrossSectionalForwardScore` rows carry the ordered complete component evidence; legacy and
direct synthetic scores may retain `None`.

ADR-142 freezes the panel-projected value and quality score mappings on every new cross-sectional
experiment because those static fundamental inputs define the `xs_value`, `xs_quality`, and
`xs_quality_value` trials just as prices do. Promotion copies only those historical snapshots into
the forward position, and registry reconstruction supplies both. A legacy fundamental graduate
without its required snapshot is left unpromoted rather than rebuilt from a later fundamentals pool.
ADR-143 closes the nested-mutation and non-finite-input gaps at both experiment and position model
boundaries: snapshots are defensive immutable copies whose finite keys must follow frozen universe
order, while JSON remains an object and retains `None` plus absent-key semantics.
ADR-144 also deep-freezes the forward position's reconstruction parameters and ordered universe.
Their JSON shapes remain object and array, but in-place mutation can no longer redirect factor
scoring, lifecycle evaluation, or panel evidence validation under an existing position identity.
ADR-145 applies the corresponding complete boundary to `CrossSectionalExperiment`: ordered
universe/strategy collections, trials and parameter maps, graduate, gate verdicts, panel manifest,
and embedded quality evidence are defensively reconstructed and recursively immutable. JSON keeps
the existing object/array schema, while reload revalidates selected-trial, graduate, gate, and
lineage relationships as one claim.
ADR-147 applies that complete boundary to the single-name `Experiment` as well. Ordered trials,
parameters, graduate and gate verdict, fundamental and valuation evidence, manifest, and embedded
quality report are defensive immutable copies. Construction and reload bind the selected trial to
the graduate and manifest, preserve ADR-079's legacy max-DSR fallback, and reject mismatched symbol
or veto evidence without changing JSON object/array shapes.
ADR-160 hardens the shared `GateResult` before it reaches either experiment graph. Its persisted
`passed` value must equal the six-component conjunction, reasons are immutable JSON-shaped evidence,
MinTRL/config identity is valid, and structured holdout fields are paired. Positive infinity remains
the defined requirement for a non-positive observed Sharpe. The probability-DSR comparison's
artifact reconstruction closes unchecked-copy inference without changing gate policy.
ADR-162 applies the same standalone boundary to the shared `Trial` and `Graduate` leaves. Parameters
are immutable JSON mappings, scalar evidence is finite and range-valid, and a graduate must carry a
passing gate plus positive, matching structured holdout geometry. Longitudinal and cross-sectional
whole-search repricing reconstructs the concrete trial subtype through validation instead of an
unchecked model copy. No statistic, selector, gate predicate, threshold, or persisted JSON shape
changes.
ADR-148 extends the boundary to `PaperPosition`: parameters, lifecycle reasons, forward curves, and
nested score evidence are defensive immutable copies. Construction, managed updates, reload, and
store writes validate lifecycle identity, evidence symbol, count/finite constraints, and any
non-empty curve's ordering and terminal returns. Legacy empty curves and evidence-null scores remain
readable.
ADR-149 applies the complete boundary to `CrossSectionalPosition`. Lifecycle reasons, score curves,
and ordered component evidence join the already-frozen reconstruction fields as defensive immutable
copies. Construction, managed replacement, reload, and store writes validate open/retired state,
finite cost and statistics, unique universe identity, evidence order/common revision, and non-empty
curve geometry. Evidence-null scores and empty curves remain supported.
ADR-150 closes the durable-write bypass for experiment pools. Monolithic and partitioned
single-name writers and the cross-sectional writer reconstruct all incoming model dumps through the
ADR-145/147 boundaries before any filesystem mutation. Retention, deduplication, and lifetime-trial
accounting are unchanged.

ADR-155 applies the same durable-boundary rule to the independent fundamentals pool that supplies
cross-sectional value and quality inputs. `FundamentalRecord` flags are defensive immutable copies;
quality/value/combined scores are finite in `[0, 1]`, F-score is in `[0, 9]`, and combined equals
quality times value exactly when both legs exist. Merge reconstructs every input record before
newest-filing deduplication, closing unchecked-copy writes without changing factor formulas or JSON
array/object shapes.

ADR-156 closes the equivalent root-boundary gap in `DataQualityReport` itself. Issue order and nested
context evidence are defensive immutable copies, context is finite JSON data, and both repository
writers reconstruct unchecked model copies before retaining or transacting. Embedded reports thus
keep one verdict and provenance under one UUID without changing checks, thresholds, or JSON shapes.

ADR-152 makes `paper-forward.yml` the sole production workflow writer of the single-name paper
portfolio. Discovery and hunt workflows persist research-pool evidence only; `scripts/paper.py`
loads the complete committed pool and idempotently promotes all eligible graduates on its next
daily run before updating open-position lifecycle evidence. Do not restore portfolio staging to a
search workflow or try to serialize unrelated workflows with one lossy GitHub concurrency group.

ADR-153 causally orders broker reconciliation after that writer. Automatic paper-broker runs are
triggered only by successful completion of `Paper forward accrual`, then explicitly read current
`master`; a clock offset is not a dependency. Manual broker recovery follows the same checkout
rule. Failed accruals must not place automatic paper orders.

ADR-154 makes daily discovery the sole automated publisher of `data/research_pool`. The retired
weekly workflow searched only a subset of the weekday discovery universe and could conflict on the
same generated symbol partitions from a stale base; its local fallback could leave a divergent
commit after push rejection. Custom/recovery sweeps use daily discovery's manual universe input.
Do not restore another automated commit/push path for the research pool.

---

## 8. Oracle tests (must pass before any Phase 4 validation)

A sophisticated statistic on a buggy engine is worthless. All in `tests/`:
- `buy_and_hold_matches_analytic`: 100%-long signal → equity matches closed-form
  `initial * close/close[0]` (within 1e-9, zero cost).
- `zero_signal_produces_zero_exposure`: all-zero signals → flat equity, 0 trades, 0 Sharpe.
- `symmetric_long_short_neutrality`: +1/−1 alternating in a trend nets ≈ 0 (costs only).
- `transaction_cost_reduces_returns_monotonically`: costs=[0,.001,.005,.01] → returns non-increasing.
- `benchmark_comparator_spx_baseline`: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.

ADR-165 gives `ResearchDataset.frame` defensive ownership. Construction captures a private numeric
OHLCV snapshot; each access returns an independent working frame, explicitly copying both axes
because ordinary pandas deep copies can share datetime-index storage. Source and returned-frame
edits cannot change the retained observations under the same quality identity. Constructor
`frame=` and `dataclasses.replace` remain supported. Arbitrary mutable object-valued cells are
outside the canonical numeric frame contract; direct supplied report/frame correspondence is not
certified by this ownership boundary.

ADR-166 makes standalone forward points/scores authoritative intrinsic evidence boundaries.
Both point families require aware UTC timestamps and finite positive equities. Both score families
revalidate instances, require aware UTC cutoffs, finite statistics and valid counts, freeze curve
lists, and bind nonempty curves to length, chronological order, terminal returns, and `as_of`.
Single-name trades cannot exceed bars; present panel evidence is immutable, nonempty, symbol-unique,
and at one revision. Position boundaries still bind symbol/universe and freeze-date identity.
Legacy empty curves, absent evidence, and historical beats flags remain supported.
