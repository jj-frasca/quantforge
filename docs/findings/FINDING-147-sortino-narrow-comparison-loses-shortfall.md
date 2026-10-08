# FINDING-147: Sortino narrow comparisons can lose a real target shortfall

- **Date:** 2026-10-07
- **Severity:** Medium — descriptive no-downside claim can be false
- **Status:** Resolved by ADR-206

## Evidence

Let `a = np.float32(.01)` and target `float(a) + 1e-12`. A float32 or nullable
Float32 Series `[a, nextafter(a, float32(+inf))]` compares below target as
`[False, False]` through Series.lt, because the target is rounded to the narrow
dtype. Validated float64 observations instead compare `[True, False]`.
ADR-205's no-downside shortcut therefore returns measured zero despite a real
negative shortfall and a finite positive exact-float Sortino. Original source
and target validation alone do not establish the arithmetic comparison contract.

This was independently reproduced offline. Sortino is descriptive only; no
production false graduate or gate effect is asserted. ADR-206 will compare the
float64 kernel observations before native arithmetic, with failing tests first.
No generated records, thresholds or calibration rates change.

## Resolution

ADR-206 compares the validated float64 values to target before the no-downside
shortcut and computes nonzero-target excess in that same kernel. Four observed
RED cases (float32/nullable Float32, ambient ignore/raise) precede correction;
independent exact-float ratios protect the measured positive score. Source and
target validation, short/no-downside semantics and thresholds remain unchanged.
