# FINDING-146: Sortino scaled-target cancellation can produce finite zero

- **Date:** 2026-10-07
- **Severity:** Medium — descriptive finite risk scores can lose near-target excess
- **Status:** Resolved by ADR-206

## Evidence

Independent research review of ADR-205 reproduced target `1.5e308` with two
returns: `nextafter(target, 0)` and `nextafter(nextafter(target, +inf), +inf)`.
The corrected native-first Sortino reports `0.0`, while a 90-digit Decimal oracle
constructed from exact input floats reports approximately `11.2249721603`.
Native summation overflows; fallback normalization followed by mean-minus-target
cancels a representable excess. Related near-target samples produce finite scores
with multiplicative errors. This is distinct from a truly unrepresentable ratio.

Sortino remains descriptive only; no gate, selector, PBO or DSR consumes it. This
is an offline arithmetic reproduction, not a production or false-graduation claim.

## Scope and next decision

ADR-205 resolves full native scale failure and explicitly leaves general finite
precision/cancellation separate. An honest nullable wire representation does not
certify every finite score. Before correction, write a new ADR and failing
exact-float tests for near-target subtraction/mean order, including representable
native compatibility, signed/nonzero targets, complete nullable inputs and strict
error modes. Preserve full-sample downside, annualization and no-downside semantics.
Do not change thresholds, rewrite generated records or quote a new calibration.

## Resolution and additional evidence

Finite native averaging also loses target excess: target `1.0` with returns one
float below and two floats above gives `44.8998886413`, versus exact-float Decimal
`33.6749164810`. ADR-206 forms original float64 per-observation excess before
nonzero-target mean; failed native arithmetic scales these differences before
stable summation, using source/target scaling only when subtraction overflows.
Twenty-eight RED regressions precede correction, covering signed ordinary/huge
targets and FINDING-147 narrow-dtype comparison. Target-zero pandas native
compatibility and an independent Hypothesis nonzero-target oracle remain.
General arithmetic limitations remain, including written FINDING-148; this
resolution certifies target handling, not every possible finite result.
