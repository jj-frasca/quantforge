# ADR-278: Match native float16/float32 benchmark moment precision

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-227
- **Extends:** ADR-277

## Context

ADR-277 matches masked Float32 benchmark variance to float64 covariance, leaving
other benchmark types intact. Native float16/float32 also round their variance
at narrower precision. Against itself, native float16 [0,0,444] publishes beta0
and alpha37312; native float32 [1e20,2e20,3e20] publishes beta0 and alpha about
5.04e22. Both have exact zero excess and finite outputs, but should have beta1/
alpha0. Float16 [1000,2000,3000] instead declines because its false alpha overflows.
Their original sample covariance is float64 representable; narrowed variance
can become infinity or underflow before the ratio. This also must be corrected
before a separate narrow-excess dispersion repair expands accepted comparisons.

## Options considered

1. Extend ADR-277's same matched-precision path to native floating widths below
   float64; preserve the old masked Float32 branch exactly.
2. Repair only excess dispersion. Would leave demonstrably wrong beta in newly
   measurable comparisons; source moment repair is the prerequisite.
3. Rewrite every beta/source estimator. Unnecessary wider scope.
4. Clip variance, cap returns or introduce an epsilon. Changes evidence/estimator.

## Decision

Define low-width benchmark as a native NumPy floating dtype narrower than float64
(float16/32) or classic masked Float32. Use ADR-277's existing temporary plain
float64 sample variance and matched plain float64 scaled recovery operands for
that family. Original covariance already extracts float64 observations and stays
unchanged. Constant, integer and genuine native wider branches still win first.
Every other benchmark type and the existing masked Float32 behavior remain.

Beta changes intentionally for the native low-width family; alpha naturally uses
corrected beta through its original formula. Original source/alignment guards,
means, excess/IR/TE/drawdown, scale restoration, metadata and state stay. No
threshold, calibration identity, workflow, schema or generated record changes.

## Evidence and limits

Independent public prototype: 1,220 Fraction beta cases across three low-width
families, 21 partners, four origins and n3–128, plus six tiny recovery cases.
Proposed public tests pass 856 cases, including three large same-series controls,
strict ordinary/state/ownership, guards, constants, overlap and meaningful affine
Hypothesis variation. Forty native float16/masked Int8 or UInt8 combinations retain
an independently written, preexisting subtraction TypeError; tests assert that
separate compatibility failure explicitly rather than skipping or fixing it here.
Repository RED is required before implementation, followed by independent final
review, full foreground make check-all and exact master CI.

Narrow source means, alpha, excess/dispersion and large integer partner covariance
retain separate limits. Tiny recovery uses caller-ignore because unchanged
means/alpha lack universal strict-state guarantees. Narrow-excess standard
variance can still publish zero risk; that is the next separate scope, not fixed
by this decision. No historical market contamination is established.

## Reversal

Restore both ADR-277 inline masked-only predicates. This reopens FINDING-227
while retaining the previously delivered masked Float32 correction.
