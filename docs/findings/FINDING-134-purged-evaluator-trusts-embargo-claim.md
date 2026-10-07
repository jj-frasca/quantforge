# FINDING-134: Purged evaluation trusts an unchecked embargo claim

- **Date:** 2026-10-07
- **Severity:** Medium — direct callers can publish overlapping selection as purged evidence
- **Status:** Resolved — ADR-198

## Evidence

For a six-row two-config matrix with first-column returns `.01` through `.06`
and the negatives in the second column, `purged_cv_evaluate` accepts train and
test rows both `[0,1]`, recording `embargo=5` and finite OOS Sharpe approximately
33.67491648. It also accepts train `[0,1]`, test `[2,3]`, `embargo=2` despite
both train rows lying inside the requested boundary exclusion. Train `[-2,-1]`
and test `[4,5]` with embargo zero alias the exact test observations.

The ordinary split generator is correctly purged; no production leak or false
graduate is claimed. The public evaluator treats embargo as reported metadata
and does not verify row identity or the exclusion interval. Finite result-model
checks cannot prove purging. Existing dropped-fold and benchmark-kept-fold tests
even supply an impossible 100-bar embargo over 40-row overlapping-boundary fixtures.

## Correction and limits

Require nonnegative nonboolean integral embargo and one-dimensional integer row
arrays with nonnegative in-range unique ascending rows. Require contiguous test
folds and exclude train rows from the closed embargo interval around each fold.
Preserve empty-fold dropping, before/after training outside that interval,
singleton tests, generator behavior, paired benchmarks and all thresholds.
Pad those kept-fold test geometries to honor the unchanged 100-bar embargo while
retaining their original count/paired-benchmark assertions. This does not make purged CV
causal: future training remains intentional (ADR-039).
