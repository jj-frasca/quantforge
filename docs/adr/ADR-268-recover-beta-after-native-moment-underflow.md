# ADR-268: Recover beta after native moment underflow

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 4, ISO 2026-W42
- **Resolves:** FINDING-217, remaining beta moment-underflow scope of FINDING-113
- **Extends:** ADR-180, ADR-181

## Context

ADR-181 recovers nonconstant benchmark variance that collapses to zero. Positive
subnormal variance can still quantize the covariance ratio, and covariance can
underflow even when benchmark variance remains normal. Finite output validation
cannot detect beta 0 instead of 0.5, or 0.5 instead of one-third. Independent exact
represented-input Fraction covariance oracles reproduce both cases.

## Options considered

1. Detect native beta underflow and reuse the existing scaled covariance ratio.
   Preserves the ordinary path and changes only arithmetic known to lose evidence.
2. Scale every comparison. Simpler uniform arithmetic, but changes ordinary native
   rounding and expands compatibility beyond the reproduced defect.
3. Add a variance epsilon or accept finite output as accurate. Either changes the
   estimator or preserves demonstrated false values.

## Decision

Evaluate native benchmark variance, covariance and beta quotient with local NumPy
underflow set to raise. If those operations signal underflow, use ADR-181's existing
separately maxabs-normalized covariance/variance branch for a nonconstant benchmark.
Retain the existing native-zero/nonconstant recovery trigger and genuine constant
benchmark beta-zero convention. Preserve native beta when no underflow occurs.
The enclosing overflow/invalid/divide handling, source guards, inner alignment,
original operands and downstream alpha/IR/tracking-error/drawdown formulas remain.

No source clipping, epsilon, threshold, statistic definition or new estimator is
introduced. Alpha naturally changes when corrected beta enters its original formula.
This descriptive comparator is not a selector/gate input; calibration identity stays.
Historical generated records remain untouched.

## Evidence and limitations

Observe RED before production changes for positive-subnormal variance, covariance
underflow with normal positive variance, signed/nullable variants and strict same-
series neutrality. Use exact represented-float Fraction covariance oracles, relative
error checks with zero absolute tolerance, Hypothesis affine samples, true constants,
all-zero strategies, caller-state/input preservation and ordinary complete baseline
comparisons. Run independent review, foreground make check-all and exact master CI.

This does not certify universal beta precision. Existing scaled covariance and scale
restoration can still lose very uneven observations or decline extreme scale ratios.
Unrelated excess dispersion, information ratio, tracking error, alpha aggregation and
log-wealth arithmetic retain their existing limitations; there is no whole-comparator
strict-error-state guarantee. Rounded centering of a true constant can also produce
a positive normal residual variance (FINDING-217 records the .1 example); this is
not underflow and stays unchanged. Further corrections need separate evidence and decisions.

## Reversal

Restore the native variance-underflow suppression and zero-only scaling trigger.
That reopens FINDING-217 without changing formulas, thresholds or persistence.
