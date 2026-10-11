# ADR-243: Refuse nonfinite power capture arithmetic

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-192
- **Extends:** ADR-045, ADR-055, ADR-059, ADR-061, ADR-219
- **Relates to:** ADR-217, ADR-229

## Context

Finite power-array elements do not guarantee finite derived capture claims.
Native even medians can overflow, yielding infinite capture, false gross zero,
or a false noise refusal. Finite reference medians can overflow the unchanged
Lo standard-error arithmetic; finite numerator/denominator division can overflow
independently. Parent and independent scratch probes reproduced these defects.
All 12 committed power cells remain compatible; no observed outcome is changed.

## Options Considered

1. Validate the existing executed arithmetic and fail closed. This preserves
   every finite native result and isolates invalid derived evidence, but refuses
   some mathematically representable ratios whose native intermediates overflow.
2. Recover medians, standard errors and ratios using alternative arithmetic.
   This admits more extreme evidence, but requires separate estimator/rounding
   contracts beyond a narrow boundary correction.
3. Return None or clamp nonfinite results. Cheap, but conflates invalid arithmetic
   with legitimate legacy/noise refusal and can publish false capture claims.

## Decision

Validate each executed native reference, finalist, history and complete-category
median; derived history years; unchanged Lo standard error; and final quotient.
Raise ValueError on nonfinite intermediates/results and normalize arithmetic
OverflowError at this capture boundary. Keep original operands and operation
order; do not retype the history median, substitute estimators or recover values.
The public frontier standard-error function remains unchanged.

Preserve existing early partial/legacy refusals and complete-category filtering.
Only evaluate numerator/category arithmetic after the existing gross positivity
or net/achievable noise predicate permits a ratio. Finite negative capture,
capture greater than one, signed zero and finite underflow keep native meanings.
No threshold, reference, procedure, fingerprint, source or generated-data change.
FINDING-155 and FINDING-159 remain Open; finite intermediate precision is outside
this scope. ADR-217's percentile recovery does not govern capture arithmetic.

## Verification and reversal

Observe failures for all four accessors, serialization and sweep reconstruction
before code. Cover median, standard-error, history and genuine quotient overflow;
protect ordinary exact native arithmetic, legacy/noise refusals and partial
categories with Hypothesis invariants. Independently compare all computed JSON
for the 12 committed cells, review and run the full foreground delivery gate.
Removing the guards reopens FINDING-192.
