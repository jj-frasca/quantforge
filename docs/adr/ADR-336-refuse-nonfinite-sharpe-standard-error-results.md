# ADR-336: Refuse nonfinite Sharpe standard-error results

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 10, ISO 2026-W43
- **Resolves:** FINDING-284
- **Extends:** ADR-334/335/043
- **Relates to:** ADR-243/292

## Context

Valid finite original inputs and intact integral squares do not guarantee a
finite returned standard error. Native NumPy floating square overflow and
native history-division overflow can return infinity. At zero Sharpe and
Python history 2**-1074, the exact model SE is the representable 2**537, but
the existing native division returns infinity before the square root.

Parent and independent exact represented-operand controls confirm the defect.
Ordinary producers use realistic source-derived history and validated float
scores; frontier and capture boundaries have additional output checks. No
actual production occurrence, affected graduate, historical rate or calibration
change is established. This finding concerns a public primitive's issued result.

## Options considered

1. Require a finite positive final result after the existing native arithmetic.
   Minimal, preserves ordinary outputs, warnings and exceptions, but refuses
   some mathematically representable answers instead of recovering them.
2. Validate intermediate squares through binary64 inspection. Adds an
   unnecessary representation restriction on exact/wider intermediate values
   and can change existing exception timing; deferred.
3. Reorder, scale or replace the arithmetic to recover extreme answers. Needs
   a separate rounding and numerical design beyond this boundary repair.
4. Trust callers to reject infinity. Mitigates ordinary producers but leaves
   the public primitive issuing unsupported uncertainty; rejected.

## Decision

Bind the result of the exact existing math.sqrt expression, require it to be
finite and strictly positive, then return that same result. Keep ADR-334's
source guards and ADR-335's native integral-square guard unchanged. Add no
normalization, intermediate inspection, exception catch, warning suppression,
NumPy errstate context, floor, cap or numerical recovery.

Native square/division exceptions still propagate under the caller's policy.
NumPy warn policy still emits its original warning before the new refusal;
ignore policy now refuses the previously returned infinity. Python floating
history overflow has no NumPy warning to suppress. Require positive uncertainty
because the model adds one over finite positive history: the zero-output guard
is preventive, not a claim of an observed ordinary native zero-SE witness.

## Consequences and limits

This validates the final claim, not every intermediate or the accuracy of a
finite estimate. Existing huge Python-int/Fraction mixed-arithmetic exceptions
remain; wider native intermediates are not newly restricted. Harmless tiny
floating square underflow and original integer zero remain valid when the
native final SE is finite and positive. General custom Real operator integrity,
finite precision and numerical recovery remain separate work.

No estimator/model, financial threshold, selector, score cap, fingerprint,
accounting-v14, frozen cohort or generated record changes. This is not evidence
that the exact mathematical SE is unrepresentable, and it does not relabel
historical outcomes or establish a changed production rate.

## Verification and reversal

Observe actual RED before runtime edits. Cover native floating square and
history-division overflow, exact power-of-two history controls, warn/ignore/
raise behavior, ordinary closed forms, harmless underflow, guard precedence and
existing native exceptions. Hypothesis checks supported finite native outputs,
signed symmetry and positive uncertainty. Preserve all 60 post-ADR335 scalar
outcomes, all 24 frontier reports and the prior runtime AST except the result
binding/guard/return and docstring. Independent review and foreground
make check-all precede individual push and exact CI verification.
Restore the inline return to reverse, reopening FINDING-284 without changing
historical evidence.
