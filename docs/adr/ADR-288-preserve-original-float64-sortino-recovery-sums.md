# ADR-288: Preserve original sums in failed Float64 Sortino downside recovery

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** Codex autonomous session 11, ISO 2026-W42
- **Resolves:** FINDING-237
- **Extends:** ADR-205, ADR-206, ADR-207, ADR-210, ADR-212

## Context

Common-scale normalization can corrupt a cancellation sum before fsum. Original
native/classic Float64 [-3e-200,1e-200,2e-200] has exact sum zero but Sortino
recovery reports -5.087681048627602e-16. A one-ULP positive residual gives an
accepted score about 42.59% low. This is a descriptive ratio, with tiny scores in
the demonstrated fixtures; no graduation or market impact has been established.

## Options considered

1. Preserve original sum and separately normalize downside in the failed domain:
   selected, keeping native measurable and outside-family results.
2. Change every recovery path or native estimator: exceeds the reproduced scope.
3. Keep common-scale cancellation: retains the documented false measurement.

## Decision

Only for original native float64/classic nullable Float64 with target zero,
select new recovery when the native downside RMS expression raises underflow
and recomputing with underflow ignored gives finite RMS, or native RMS collapses
to finite zero despite an original negative observation. Isolate this expression
from native mean and ratio arithmetic. Nonfinite RMS, mean/ratio-only failure,
nonzero targets and other source families retain the previous path.

Certify the original float64 sum with math.fsum before normalization. If fsum
intermediate overflow prevents certification, retain the prior fallback. Exact
original cancellation returns zero. Otherwise normalize original negative
shortfalls by their own positive maxabs, compute RMS over the full sample, and
combine original sum/downside scale mantissas with sqrt(252), RMS and sample
count before restoring the exponent difference once. Preserve legitimate
subnormal and signed-zero rounding; final overflow or unmeasurable recovery is
None under ADR-205. No risk floor, ratio cap or change in downside definition.
Validation and short/no-downside precedence, caller observations and floating
state remain. O(n) time/memory without dependencies or mutable caches.

Selected cancellation fixtures use exact Fraction moments and agreeing Decimal
200/800 oracles. Subnormal controls use exact squared rational midpoints and
ADR-212's one-output-ULP precision allowance. Universal correctly rounded
recovery and arbitrary nonzero native reduction accuracy are not established.

Sortino remains descriptive: accounting stays v11 and current-version calibration
remains unmeasured. Frozen historical cohorts, thresholds, selector, grid, budget,
schema and generated records remain unchanged.

## Verification

Require genuine public RED before implementation, independent scope and final
review, STD/RMS failure-provenance tests, Hypothesis signed cancellation controls,
exact outside/native/nonfinite baselines, final signed zero and range boundaries,
existing financial property domains, foreground make check-all and exact CI.
Independent scratch scope passed 252 Fraction/Decimal oracles and 28 extra signed
midpoint controls; 100k-observation prototype took approximately .0075 seconds.

## Reversal

Restore ADR-210's common-scale sum in this domain, retaining the written finding
and original calibration attribution. This reopens FINDING-237.
