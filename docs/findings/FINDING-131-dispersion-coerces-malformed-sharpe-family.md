# FINDING-131: Dispersion coerces malformed Sharpe families

- **Date:** 2026-10-07
- **Severity:** Medium — malformed trial evidence can become a multiplicity price
- **Status:** Resolved — ADR-196

## Evidence

`robust_sharpe_dispersion([True, False])` and the string family `['0', '1']`
both report sample dispersion approximately 0.70710678. A nested two-row family
`[[0, 1], [2, 3]]` reports approximately 1.29099445: NumPy standard deviation
flattens four values although the family-length branch selected the two-candidate
rule. Boolean/string coercion and nested geometry are not measured candidate
Sharpe estimates. Whole-search margin and probability accounting share this helper.
Normal production callers supply one finite float per evaluated candidate; no
corrupt persisted record or false graduate is claimed.

## Correction and limits

Validate each original family element as a finite float-representable real
nonboolean scalar before array conversion. Nested families then fail instead of
being flattened. Preserve signed/numpy/Fraction scalars, too-few precedence,
candidate count, IQR/sample estimator, floor, thresholds and calibration identity.
