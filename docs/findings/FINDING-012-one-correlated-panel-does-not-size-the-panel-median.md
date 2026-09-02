# FINDING-012: One correlated null panel does not size the panel median

- **Severity:** High — a plausible follow-up can repeat ADR-075's independence error under a new
  generator name
- **Found:** 2026-08-30 by Codex design review of ADR-075's correlated-panel follow-up
- **Status:** ADR-081 identity/consolidation hardened; generation and measurement pending
- **Affected:** ADR-075, `null-calibration.yml`, `NullCalibration`, `_clustered_difference_ci`

## Finding

ADR-075 correctly states that its interval is too narrow because 66 real symbols share one calendar
window, then calls a correlated-panel null “the fix.” Generating one joint 200-symbol null panel is
necessary but not sufficient. It provides one correlated realization of the panel median. The
current comparison would still resample the 200 resulting symbol-level excesses independently and
therefore erase the dependence the new generator was built to preserve.

The sampling distribution needed by ADR-075 is the distribution of a **panel statistic** under the
null. Estimating it requires independent panel-level replicates, each carrying the whole dependent
cross-section through the unmodified search, or a different pre-specified dependence-aware
instrument built from time/fold-level observations. Correlated columns inside one calibration do
not create those replicates.

## Evidence

- `_clustered_difference_ci` samples `null_excess` element by element with `rng.choice`; it has no
  panel identity to resample.
- `NullCalibration` stores flat finalist-diagnostic lists and no `panel_replication_id` or
  per-panel median.
- ADR-037 and `null-calibration.yml` explicitly rely on null symbols being independent and merge
  symbol shards. A correlated panel invalidates that execution assumption unless every shard uses
  the same synchronized panel draw and consolidation preserves its identity.
- One jointly row-resampled source panel yields one value of `median(null excess)`. Treating its 200
  correlated symbol values as 200 bootstrap units recreates the under-width defect rather than
  measuring between-panel variation.

## Impact

The existing ADR-075 result remains explicitly a lower bound on its own width; this finding does not
change a graduation, threshold, or generated artifact. It prevents the next implementation from
claiming that contemporaneous correlation alone repairs the confidence interval when the reporting
statistic still assumes independent null draws.

## Required design before implementation

1. Pre-state the panel-level estimand and the number of independent panel realizations needed to
   resolve a decision-relevant effect before observing their results.
2. Preserve panel identity in the artifact and resample/compare panel statistics, never individual
   correlated symbols as if independent.
3. Make the generator destroy the serial predictability catalog strategies trade while preserving
   the contemporaneous dependence being tested, and measure what joint-row resampling loses about
   persistent market regimes.
4. Replace or redesign ADR-037's independent-symbol sharding; a partial panel is not an independent
   null sample.
5. Do not dispatch the expensive repeated-panel experiment under a no-cloud/no-billable-runner
   mandate. Code mechanics can be tested locally, but no headline changes without the authorized
   full measurement.

## Accepted design

ADR-081 freezes the missing design without spending the measurement: equal weight per real symbol,
joint iid resampling of complete calendar vectors, 400 independent whole-panel replicates, exact
source/cohort/search identity, and a separate manual workflow sharded only by complete panel index.
The ADR-075 headline and lower-bound qualification remain unchanged until an authorized completed
artifact is interpreted under a later ADR.

The first implementation slice is intentionally non-measuring: `panel_null.py` makes the whole
panel an indivisible, globally indexed artifact and refuses partial/mixed consolidation. It does not
yet generate a correlated panel, compute tail inference, dispatch a workflow, or change the headline.
Direct final-artifact construction now enforces the same complete-panel invariants, and all persisted
real/panel statistics must be finite.
