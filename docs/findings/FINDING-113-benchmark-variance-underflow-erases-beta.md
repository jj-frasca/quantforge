# FINDING-113: Benchmark variance underflow erases beta

- **Date:** 2026-10-07
- **Severity:** Medium — finite extreme-scale statistics can be numerically wrong
- **Status:** Collapsed benchmark variance resolved by ADR-181; other tiny-moment limitations remain

## Evidence

Identical nonconstant strategy and benchmark `[1e-200, 2e-200, 3e-200]` returns publish beta
zero and annualized alpha `5.04e-198` rather than the same-series oracle's beta one and alpha
zero. Sample variance squares underflow to zero, selecting the constant-benchmark convention even
though the source has distinct observations. Under strict NumPy error settings the variance
computation raises an underflow FloatingPointError. Research-expert reproduction agrees.

## Correction and remaining scope

ADR-180's finite-output guard does not resolve this: all wrong outputs here are finite.
ADR-181 scales the same covariance ratio only when native benchmark variance is zero despite
distinct observations. Decimal covariance and Hypothesis tiny-scale affine oracles verify beta
and alpha; true constant benchmarks and native positive-variance arithmetic retain their prior
semantics. No variance epsilon, clipping or threshold change is introduced.

Positive but subnormal variance quantization and covariance underflow while benchmark variance
remains positive are not repaired by this branch; neither are other tiny-scale IR/tracking-error
limitations. A wider numerical audit needs its own stable-moment decision and oracle tests before
changing those calculations. No generated data was modified.
