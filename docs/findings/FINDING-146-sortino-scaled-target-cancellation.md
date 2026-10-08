# FINDING-146: Sortino scaled-target cancellation can produce finite zero

- **Date:** 2026-10-07
- **Severity:** Medium — descriptive finite risk scores can lose near-target excess
- **Status:** Open

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
