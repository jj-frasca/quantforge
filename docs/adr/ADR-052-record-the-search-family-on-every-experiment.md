# ADR-052: Record the resolved search family on every experiment

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-044 (version the calibrated search space), ADR-032 (symbol-partitioned pool)
- **Relates to**: ADR-038/039 (OOS diagnostics), ADR-051 (finalist diagnostics), FINDING-001

## Context

ADR-044 closed FINDING-001 for calibration artifacts: `NullCalibration` and `PowerCalibration` both
carry a `search_config_version` that fingerprints the resolved hypothesis family — the budgeted
grids, `n_per_param`, the refinement settings, and the trial-accounting method — so a Type-I or
power number can never be read as current merely because the six gate thresholds did not change.

The research pool got no such field, and the omission has a cost that is no longer hypothetical.
Executing ADR-038/039's revisit trigger this session meant comparing the pool's out-of-sample
diagnostics against `data/null_calibration/*.json`. The comparison is only meaningful if both sides
resolved the same hypothesis family, and establishing that required reconstructing the lineage from
outside the data entirely: the null artifacts were committed at 06:32 UTC, `_TRIAL_ACCOUNTING_VERSION`
went to `v3` at 07:41 UTC, and the discovery run that wrote the pool started at 08:48 UTC — so the
two sides were a version apart. Nothing in either the pool or the report said so. It was found by
diffing commit timestamps against workflow start times, which is not a method.

An `Experiment` that cannot name the search family that produced it cannot be matched to the
calibration that judges it. That makes the pool's every comparison against a calibration an
argument from timestamps.

## Decision

**`Experiment.search_config_version`, computed by `run_search` with the same function the
calibration path uses.**

`calibration_search_version(...)` is called with the run's own `strategy_names`, `n_per_param`,
`GateConfig`, and refinement settings, so equality of the two strings is exactly the claim "these
were produced by the same resolved hypothesis family" — the only claim a real-versus-null comparison
needs, and the one that was previously unavailable at any price.

`PoolReport` surfaces the versions present with their experiment counts, and `scripts/pool_report.py`
prints them beside the OOS diagnostics, because a pool that mixes families is a pool whose single
median is a blend of two different procedures.

## Alternatives considered

- **Record it on `Trial` instead.** Rejected. It is a property of the run, not of a candidate, and
  it would repeat the same hash 34 times in every experiment — the pool-size failure ADR-032 solved.
- **Recompute the fingerprint at read time from today's catalog.** Rejected, and it is the trap
  worth naming: that answers "what would this family be now", which is precisely the question that
  conceals drift. The point of the field is that it is a fact about when the row was written.
- **Store the full resolved grid on the experiment.** Rejected for the same size reason as the
  first alternative. Nothing downstream needs the grid; comparisons need identity.
- **Backfill the 3,237 existing rows.** Rejected as unsound: the family those runs used cannot be
  reconstructed, and a synthesized value would be indistinguishable from a measured one. They read
  back as `legacy-unspecified`, which is the honest answer.

## Consequences

- One extra `allocate_catalog_candidate_budget` per experiment. Measured at **23 ms** against a full
  34-strategy search that takes seconds to minutes; not worth an optimization that would risk the
  two fingerprints diverging.
- The pool becomes self-describing: `pool_report.py` shows whether the rows it is summarizing came
  from one search family or several, without reference to git history.
- **Cross-sectional experiments are deliberately out of scope here** and keep no such field. They
  have no null calibration to be compared against yet, so the field would record an identity nothing
  reads. Stated rather than left silent, so the asymmetry is a decision and not an oversight.

## Reversal

Drop `search_config_version` from `Experiment` (it is defaulted, so records written under this ADR
still load), remove the `run_search` call, and delete `PoolReport.search_config_versions` and its
report line. No threshold, gate, or promotion rule reads any of it.
