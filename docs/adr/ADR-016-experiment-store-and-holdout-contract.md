# ADR-016: Experiment store, holdout contract, and GateConfig (StrategyLab Phase 1)

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Joe Frasca
- **Implements**: ADR-014 (harness), ADR-015 (data/statistical policy)

## Context
Phase 1 of the StrategyLab needs three things pinned before any search can run honestly: how a
finding is **recorded** (the trial-counted research pool), how the **holdout** is kept
structurally unreachable during search, and how the tunable **gate thresholds** are represented
and versioned. ADR-014/015 decided the *why*; this ADR fixes the *shapes*.

## Decision

### 1. Holdout contract — unreachability by type, not convention
`split_holdout(frame, symbol, holdout_fraction=0.2, min_holdout_bars=252)` returns a
**`SearchDataHandle`** (the in-sample head — the ONLY data any search tool accepts) and a
**`SealedHoldout`** (the most-recent tail). The holdout frame is private to `SealedHoldout`;
the sole way to use it is `score_on_holdout(sealed, strategy) -> HoldoutScore`. Search-side
functions are typed to take `SearchDataHandle` and **never** `SealedHoldout`, so a leak is a
type error, not a silent bug (ADR-014/015 requirement). Split is contiguous and time-ordered:
holdout is always the calendar-latest `max(holdout_fraction·N, min_holdout_bars)` bars.

### 2. GateConfig — versioned, tunable, recorded
A frozen `GateConfig` carries the thresholds (`dsr_min`, `pbo_max`, `stability_min`,
`holdout_sharpe_min`, `trial_budget`) plus a deterministic `version_hash` (SHA256 of its
fields, via the existing `compute_parameter_hash`). Every experiment records the exact
`GateConfig` that judged it, so a result is always reproducible against its rubric and the
calibration loop (ADR-015) can compare outcomes across config versions.

### 3. MinTRL gate — statistical-power check
`minbtl_years(n_trials, annualized_sharpe)` implements Bailey & López de Prado's Minimum
Backtest Length approximation `≈ 2·ln(N)/SR²`. A candidate passes MinTRL iff its track-record
length (years) ≥ `minbtl_years(lifetime_trials, observed_sharpe)`. This is the "is there even
enough data for this claim, given how hard we searched?" gate.

### 4. GraduationGate — deterministic verdict
`evaluate(report, track_record_years, n_trials, holdout, config) -> GateResult` returns a
`passed: bool` + per-check booleans + human reasons. Pure and tested; the agent may rank and
explain survivors but cannot override the verdict. Predicate: `deflated_sharpe > dsr_min` AND
`pbo < pbo_max` AND `parameter_stability_score ≥ stability_min` AND MinTRL passes AND
`holdout.sharpe > holdout_sharpe_min`.

### 5. Experiment record — the research-pool unit
An `Experiment` bundles: `ExperimentManifest` (existing lineage), the search space, the
`GateConfig` (+ version_hash), **all** trials (`config + in-sample metrics + validation summary`,
not just the winner), `n_trials`, the graduate (winner + `GateResult` + `HoldoutScore`) if any,
and the agent's rationale. `ExperimentStore` is a protocol with an in-memory/JSON-file impl now
(no DB dependency — mirrors the `PriceBarRepository` in-memory/Timescale split); a Timescale
table and, later, vector search over rationales are additive (ADR-015: structured first).

## Options Considered
- **Holdout hidden by convention/docstring only.** Rejected — the whole methodology dies to one
  accidental read; the type split makes leaks mechanical failures.
- **DB-first experiment store.** Deferred — needs Docker/Timescale running; the JSON/in-memory
  store is testable now and the interface lets the DB impl drop in later (ADR-009 pattern).
- **Store only winners.** Rejected — the DSR penalty and MinTRL both need the *full* trial count;
  discarding losers throws away the denominator that keeps us honest.
- **Hardcoded thresholds.** Rejected by ADR-015 (continuous calibration).

## Consequences
- Phase 1 lands as tested primitives (`holdout`, `gate`, `store`) with zero new infra, unblocking
  the Phase 2 search orchestrator.
- A graduate is a reproducible tuple: manifest hash + GateConfig version + holdout score.
- New obligation: keep search-tool signatures `SearchDataHandle`-only so unreachability holds.
- The JSON store is single-process; concurrent multi-agent writes wait for the DB-backed impl.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
