# FINDING-132: Dispersion publishes a nonfinite native scale

- **Date:** 2026-10-07
- **Severity:** Medium — public dispersion can emit unusable multiplicity evidence
- **Status:** Resolved — ADR-196

## Evidence

For the complete finite family `[1e308, -1e308, 1e308, -1e308]`, the IQR
subtraction overflows and `robust_sharpe_dispersion` publishes infinity. The
mathematical IQR scale is approximately 1.4826e308, within double range, but the
native intermediate is unrepresentable. Tiny-family sample variance similarly
overflows for large finite scores. The shared expected-max helper already refuses
nonfinite dispersion, so normal whole-search persistence is protected; the public
primitive itself still emits undefined evidence and strict NumPy mode can raise
FloatingPointError outside its ValueError contract.

## Correction and limits

Decline nonfinite native dispersion with ValueError before the existing positive
floor, using local overflow/invalid handling so strict NumPy mode has the same
refusal. Preserve native finite estimates and the degenerate floor. This does not
recover mathematically representable extreme scales, rewrite the estimator,
change a threshold or authorize calibration dispatch/generated-data edits.
