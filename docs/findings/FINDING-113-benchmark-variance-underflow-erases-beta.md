# FINDING-113: Benchmark variance underflow erases beta

- **Date:** 2026-10-07
- **Severity:** Medium — finite extreme-scale statistics can be numerically wrong
- **Status:** Open — requires a separate stable-estimator decision

## Evidence

Identical nonconstant strategy and benchmark `[1e-200, 2e-200, 3e-200]` returns publish beta
zero and annualized alpha `5.04e-198` rather than the same-series oracle's beta one and alpha
zero. Sample variance squares underflow to zero, selecting the constant-benchmark convention even
though the source has distinct observations. Under strict NumPy error settings the variance
computation raises an underflow FloatingPointError. Research-expert reproduction agrees.

## Scope and next action

ADR-180's finite-output guard does not resolve this: all wrong outputs here are finite.
A later slice should pre-register scaling/centering moment estimation with an independent
high-precision covariance oracle and Hypothesis scale invariance, preserving genuinely constant
benchmark beta zero and ordinary native arithmetic. Do not fix this by a variance epsilon,
return clipping or threshold changes. No production/data modifications accompany this finding.
