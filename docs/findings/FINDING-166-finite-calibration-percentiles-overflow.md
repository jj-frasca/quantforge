# FINDING-166: Finite calibration percentiles overflow

- **Date:** 2026-10-08
- **Severity:** High — published diagnostic arithmetic
- **Status:** Resolved by ADR-217
- **Reproduced revision:** `9091fbd9`

The shared `_percentiles` helper reports `(inf, 1e308, 1e308)` for two
`1e308` scores: NumPy sums the two median endpoints before division.
For `[-1e308, 1e308]` it reports `(0, -inf, 1e308)`: p95 interpolation
subtracts endpoints and overflows, yielding a percentile below every sample.
Independent rational interpolation at the existing binary 0.95 weight gives
p95 `8.999999999999999e307`. Equal signed maximum-float scores also have
representable medians. These are finite input scores accepted by the evidence
contracts, not malformed observations.

Both null OOS summary properties and both gross/net power reference properties
share this helper. This is a synthetic boundary reproduction; no corrupt
committed artifact, wrong observed gate verdict or false graduate is claimed.

ADR-217 specifies native-first recovery only for nonfinite summaries, keeping
finite native outputs and the existing linear virtual index. Invalid summary
source evidence must be rejected, never dropped or replaced. Empty arrays remain
unmeasured. No threshold, sample, fingerprint, reference rule or data changes.
Other percentile consumers and native finite precision remain separate limits.

## Correction and verification

Thirty rejection/recovery cases failed before correction, with five native or
empty compatibility cases already passing. All 35 new cases now pass, including
Hypothesis point-mass and opposite-sign extreme quantile invariants. Independent
review passed 279 affected tests, preserved all 16 null and 24 power summaries
across eight null artifacts and 12 power cells read-only, and checked 210 ordinary
native tuples plus caller error-state restoration. The full foreground gate
is required before delivery. No generated artifact or gate behavior changed.
