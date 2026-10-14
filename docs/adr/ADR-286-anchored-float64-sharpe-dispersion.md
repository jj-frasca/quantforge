# ADR-286: Recover Float64 Sharpe dispersion from anchored differences

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 9, ISO 2026-W42
- **Resolves:** FINDING-235
- **Extends:** ADR-203, ADR-209

## Context

Native/classic Float64 nonconstant returns near 1e-200 lose variance in native
standard deviation. Existing recovery divides original levels by their maximum
magnitude, rounding away represented differences. For three consecutive Float64
values beginning at 1e-200, the accepted positive Sharpe is
9.043156280963163e16 against exact represented-sample 1.0944783154858846e17.
Both signs and both source families reproduce this error. This scorer feeds
search, holdout and graduation; correction requires a new accounting identity.

## Options considered

1. Anchor differences before scaling only the failed Float64 dispersion. Preserves
   represented near-equal differences and existing ordinary native estimates.
2. Replace all native estimates with exact rational moments. Broader rounding and
   computational changes than the demonstrated failure requires.
3. Keep level normalization or repair only the mean. Neither repairs the observed
   dispersion error.

## Decision

For original native Float64 or classic nullable Float64 only, select anchored
recovery when the native STD call raises underflow and recomputing it with underflow
ignored yields finite dispersion, or native STD returns finite zero for a validated
nonconstant sample. Detect failure inside the STD call: mean/ratio-only failures,
nonfinite STD and other source families retain the prior recovery path.

Subtract the first original observation, then normalize differences by their
maximum magnitude and compute sample STD. Sum original observations with fsum;
combine sum and difference-scale mantissas before restoring their exponent
difference once. Preserve true zero and representable subnormal output; reject
nonfinite/unmeasurable moments or unrepresentable output with the existing error.
Validation and short/constant conventions precede recovery. Caller data and
floating-point state remain unchanged. O(n) time and memory; no cache or new dependency.

Normalized differences contain zero and a unit-magnitude observation, bounding
sample STD away from collapse for supported array lengths. This is a bounded
floating recovery, not a universal correctly rounded STD claim. Selected nearconstant
fixtures use exact Fraction moments and agreeing Decimal 200/800 oracles; broad
subnormal controls permit one output ULP checked by exact squared midpoints.

Advance trial accounting to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-v11`.
Preserve attribution of historical v10 evidence and its exact fingerprint. Current
v11 calibration distributions are unmeasured. Do not rerun, redraw or relabel frozen
cohorts. No threshold, grid, budget, schema or generated data change.

## Evidence and limits

Read-only independent scope review approved twelve literal failures, 180 exact
nearconstant/mixed-sign oracles, 40 cancellation/rounding controls, 24 exact
subnormal midpoint checks, 308 exact outside-family/nonfinite-STD baselines and
316 existing financial tests. A 100k-observation prototype took about .01s.
Require genuine public RED before code, source/failure-provenance tests, Hypothesis,
v10 restoration, independent final review, foreground make check-all and exact CI.
No actual false graduate or historical market contamination has been established.

## Reversal

Restore prior dispersion recovery and accounting identity together; retain the
written finding and historical evidence rather than relabeling observations.
