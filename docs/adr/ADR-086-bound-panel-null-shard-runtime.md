# ADR-086: Bound panel-null shard runtime below the job ceiling

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-022
- **Extends:** ADR-081

## Context

ADR-081 correctly makes a complete correlated panel the indivisible sampling unit, but its original
workflow placed ten 39-symbol panels in each job. That is 390 serial full-production searches under
a 360-minute timeout. A representative 7,400-bar search measured 44.78 seconds locally, implying
about 291 minutes before runner slowdown or setup. The topology therefore approaches the hard job
ceiling even on the faster observed host.

The 400 replicate count, global-index seed derivation, cohort, estimator, and inference thresholds
are already fixed. Shard width is execution topology only: `panel_seed(base_seed, panel_index)` makes
the union invariant to where job boundaries fall.

## Decision

Run four complete panels per shard across 100 shards, with the existing maximum of ten concurrent
jobs. Each job owns one half-open global-index range and performs at most 156 symbol searches. The
union remains exactly indices 0 through 399, every panel remains within one job, and consolidation
continues to reject any missing or duplicate index.

The preparation job receives a 120-minute timeout because ADR-085 added 39 serial observed searches
before it can freeze the shared input pair. This is deadline headroom only; it does not alter the
search, cohort, measurement, or inference.

## Alternatives considered

1. **Retain ten panels and rely on the six-hour timeout.** Rejected: the measured baseline leaves
   little allowance for a slower hosted runner and no room to raise the platform ceiling.
2. **Split symbols within a panel.** Rejected: a partial symbol shard is not an independent panel
   observation and would reopen the sampling-unit defect ADR-081 resolved.
3. **Parallelize searches inside one job.** Rejected: standard runners expose limited CPU, while
   process scheduling adds a second failure and reproducibility surface without changing total work.
4. **Change the replicate count.** Rejected: that changes the pre-registered measurement after its
   design was fixed. Shard topology can solve the execution problem without touching inference.

## Consequences

- Each batch job has substantially more deadline margin.
- The workflow creates 100 small shard artifacts and takes more matrix waves at bounded concurrency.
- Total search work, seeds, diagnostics, validation thresholds, and final artifact identity are
  unchanged.
- The workflow remains manual and unspent; this ADR does not authorize dispatch.

## Reversal

Shard width may be changed again before dispatch if an evidence-backed runtime model requires it,
provided the complete global-index set and indivisible-panel boundary remain statically enforced.
