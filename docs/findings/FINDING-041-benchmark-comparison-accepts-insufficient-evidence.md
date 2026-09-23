# FINDING-041: Benchmark comparison accepts insufficient evidence

- **Severity:** High
- **Status:** Resolved by ADR-112
- **Found:** 2026-09-23, Codex autonomous session 8
- **Affects:** Benchmark comparison and benchmark-relative drawdown

## Finding

ADR-013 requires `benchmark_comparison` to be null when there are insufficient overlapping bars,
but the API rejects only an empty alignment. One overlapping observation reaches sample variance,
covariance, and standard deviation calculations and produces `NaN` alpha/tracking error. The
response therefore exposes malformed evidence or fails serialization instead of degrading to the
documented null comparison.

The relative-drawdown calculation also begins at the first post-return relative-equity value. An
initial strategy loss relative to the benchmark becomes the starting peak and reports zero
drawdown, repeating the initial-baseline omission corrected for absolute drawdown by ADR-110.

## Required correction

Require at least two aligned finite observations whose gross returns preserve positive wealth.
Make the public comparator fail closed and let the optional API helper convert that failure to
`None`. Prepend unit relative wealth before measuring drawdown. Add regressions for one-row overlap,
invalid returns, and first-period relative loss. Do not alter any gate or validation threshold.
