# FINDING-144: Higher-moment underflow publishes false kurtosis

- **Date:** 2026-10-07
- **Severity:** Medium — unmeasurable fourth moments can become finite PSR inputs
- **Status:** Resolved — ADR-204

## Evidence

`return_moments(pd.Series([1., 2., 3., 4., 5., 9.]))` gives skew approximately
1.19324269 and raw kurtosis 4.66875. Scale every observation by `1e-100`: the
helper gives the same skew but raw kurtosis 3.0, despite higher standardized
moments being invariant to a common positive scale. Native fourth-moment or
denominator arithmetic underflows; the finite-output guard cannot detect the
fabricated answer. Under strict NumPy state, the call instead raises
FloatingPointError from scalar power. At scales `1e-150` and `1e-200`, ordinary
calls give None while strict calls raise underflow during multiplication/squaring.

PSR can therefore consume finite partial moment evidence or callers can lose the
existing nullable-unmeasured behavior solely through ambient error state. These
direct synthetic results do not establish a production false graduate.

## Correction and limits

Detect underflow around native moment arithmetic and return None, consistently
across ordinary and strict state. Keep malformed-source ValueError and complete
short/constant precedence outside that catch. Preserve native estimators and
full sample count; do not replace skew/kurtosis with a normalized estimator in
this correction. Former finite moment evidence becomes explicitly unmeasured,
so advance calibration identity. This detection does not certify every remaining
finite estimate's accuracy. No threshold, data or workflow changes.
