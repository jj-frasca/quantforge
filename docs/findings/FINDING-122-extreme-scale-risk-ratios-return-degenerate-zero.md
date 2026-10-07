# FINDING-122: Extreme-scale risk ratios return degenerate zero

- **Date:** 2026-10-07
- **Severity:** Low — extreme finite scale collapses native risk arithmetic
- **Status:** Open — separate numerical-estimator review required

## Evidence

sharpe_ratio([1,2,3,4]) is approximately 30.740852 while the same values scaled by 1e-200 or
1e200 return 0.0. Native sample variance underflows or overflows, entering the degenerate fallback.
sortino_ratio([1,-2,3]) is approximately 9.165151; scaling by either factor likewise returns zero
with default target zero. True risk variation has not disappeared. Source-validity fixes do not
address this finite-arithmetic behavior. Large-scale arithmetic can also emit overflow warnings.

## Next action and limits

Investigate scale-safe evaluation with independent high-precision oracles before modifying native
fallback conventions. Distinguish genuine constant/no-downside samples from collapsed arithmetic,
and preserve ordinary-scale estimator semantics. These scales are far from normal market evidence;
no observed production misclassification is claimed. No thresholds or generated records change.
