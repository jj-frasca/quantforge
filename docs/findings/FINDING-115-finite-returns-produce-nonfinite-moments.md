# FINDING-115: Finite returns produce nonfinite moments

- **Date:** 2026-10-07
- **Severity:** Medium — a moment evidence record can carry undefined arithmetic
- **Status:** Resolved by ADR-182

## Evidence

`return_moments([1e100, 2e100, 3e100, 4e100, 5e100])` returns an n=5 record with NaN kurtosis,
despite finite source values and sample standard deviation. Higher-order moment intermediates
overflow. Independent research-expert reproduction confirms warnings rather than explicit absence.
This differs from FINDING-114: complete source evidence can still have unmeasurable native moments.

## Correction and limits

ADR-182 preserves the estimators but returns None when computed skew or raw kurtosis is nonfinite,
matching the existing unmeasurable-variance convention. Local upper arithmetic handling supports
that refusal under strict NumPy settings. Representable ordinary moments are unchanged. This does
not implement a scaled extreme estimator or repair every precision/underflow limitation. Downstream
probability routines already decline invalid moments; this corrects the standalone evidence record
rather than asserting a false persisted probability. No data or threshold changes.
