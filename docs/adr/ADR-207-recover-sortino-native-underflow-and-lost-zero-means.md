# ADR-207: Recover Sortino native underflow and lost zero means

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-148, FINDING-149
- **Extends:** ADR-205, ADR-206

## Context

Finite native downside moments can conceal partial square underflow, and a finite
zero mean can conceal lost sum evidence. F148/F149 independently reproduce both
with representable exact-float Sortino ratios. Merely accepting finite native
score/dispersion is insufficient to establish those particular measurements.

## Options considered

1. Detect native underflow and certify zero means before preserving native scores:
   selected, using the existing cancelling-scale recovery.
2. Keep finite inaccurate scores: retains written errors.
3. Replace all native arithmetic: unnecessarily changes measurable ordinary
   estimator behavior. Precision of every nonzero native result remains separate.

## Decision

Retain unchanged validation, float64 no-downside comparison, singleton precedence,
ADR-206 per-observation excess and required nullable representation. In the native
moment/mean/ratio block, locally raise on NumPy underflow and route detected
FloatingPointError to the existing scaled recovery. Other ambient error-state
handling stays local. Underflow must not escape as a caller-state-dependent error.

If a native score would otherwise be accepted with zero mean, require math.fsum
of original float64 excess to be zero too. A demonstrably nonzero stable sum or
unrepresentable fsum intermediate instead routes to scaled recovery. Native
nonzero finite measurable scores and genuine zero cancellation remain unchanged.
This certifies lost-zero evidence, not every finite reduction's accuracy.

## Verification and limits

RED exact-float 800-digit Decimal regressions precede correction: native mean
underflow, partial downside-square underflow, signed residual cancellation and
strict/ignore error states with nullable samples. Hypothesis cancellation-residual
scales and existing financial cost/sign domains protect meaningful invariants.
Explicit true cancellation and legitimately rounded tiny-zero oracles remain.

Recovery can still lose extremely small normalized observations; no universal
precision guarantee is made for source subtraction, positive native moment
rounding, or ordinary nonzero mean cancellation. The ratio definition, full sample
count, annualization and no-downside convention remain. Sortino is descriptive
only: calibration identity v9, every validation threshold and generated evidence
remain unchanged; no workflow dispatch or paid resource.

## Reversal

Restore ambient native underflow-ignore handling and accept finite native zero
without original-excess sum evidence. This reopens both findings.
