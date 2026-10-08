# FINDING-150: Annualized volatility hides native variance failure

- **Date:** 2026-10-07
- **Severity:** Medium — descriptive annualized risk evidence is false
- **Status:** Resolved by ADR-208

## Evidence

BacktestMetrics.from_series for `[-.01,.02,-.03,.04]` reports annualized volatility
approximately `0.49355850717012273`. Scaling the same observations by `1e-200`
reports `0.0`, although volatility scales linearly and its approximately
`4.9355850717e-201` value is representable. Native pandas sample variance
underflows. Under strict ambient NumPy state the same input may instead raise
FloatingPointError, preventing publication of otherwise valid metrics.

Exact constant `[.1]*12` reports approximately `2.3009903306e-16` volatility,
although its sample variance is mathematically zero. Rounded mean subtraction
fabricates dispersion; the shared Sharpe already recognizes constants as zero.

The direct metric contract is independently reproduced offline. Annualized
volatility is passed to API/UI only; no gate, PBO, DSR or selector consumes this
field. No production false graduate is asserted. ADR-208 will require failing
independent sample-variance tests before the narrow correction, preserving native
measurable nonconstant results and the existing numeric wire representation.

## Resolution and limits

ADR-208 validates source before short/exact-constant zero, preserves measurable
native positive sample volatility and recovers detected underflow/nonfinite native
results through normalized sample std. Annualization precedes restoring scale,
so `[0, smallest-subnormal]` retains measurable annualized volatility. Twenty-four
RED cases precede code; independent 800-digit sample-variance and Hypothesis scale
oracles protect the formula. Truly unrepresentable output raises explicitly;
ordinary nonconstant native results retain exact operation order. Finite-result
precision and normalized near-constant rounding remain possible; no threshold,
calibration identity or numeric wire shape changes.
