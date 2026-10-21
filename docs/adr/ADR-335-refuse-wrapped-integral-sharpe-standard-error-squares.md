# ADR-335: Refuse wrapped integral Sharpe standard-error squares

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 10, ISO 2026-W43
- **Resolves:** FINDING-283
- **Extends:** ADR-334/043
- **Relates to:** ADR-298

## Context

ADR-334 validates original Sharpe/history evidence while deliberately retaining
native arithmetic. NumPy int8(100) squares to 16 and gives SE1.015749 instead of
the Python-int control4.565224. int8(12) squares negative and gives SE below the
null standard error; int8(16) squares to zero and gives the null SE for a nonzero
score. Larger signed/unsigned types also wrap silently. Source validity alone
does not establish that the native square represents its original integer.

Parent and independent synthetic probes confirm the defect. Current frontier,
category report and capture producers ordinarily supply float scores; no actual
production occurrence, affected graduate, historical calibration or rate change
is established. This is a standalone public primitive repair.

## Options considered

1. Check native integral square integrity against exact Python integers.
   Small, preserves safe native arithmetic and refuses wrapped evidence.
2. Normalize all scores to float or calculate with the exact replacement square.
   Recovers some values but changes calculation operands and rounding beyond
   this repair; rejected.
3. Require only a nonnegative square or finite result. Misses positive and zero
   wraps and cannot establish the advertised squared score; rejected.
4. Repair all floating intermediate/result arithmetic too. Separate domain and
   numerical-policy decision; deferred rather than implied by this check.

## Decision

After ADR-334's original guards, execute sharpe**2 once in its existing native
type. For an original numbers.Integral score, require the native square itself
to be Integral and its Python-int value to equal int(original)**2. Compare only
Python integers to avoid NumPy mixed-promotion errors. The exact value is solely
an inspection oracle; keep the native square in the unchanged division/addition/
history-division/sqrt sequence. Type aliases used for static inspection do not
replace calculation operands. A mismatch raises a named ValueError before any
division or square root. Add no exception catch, errstate or warning filter.

Requiring an integral square also refuses custom int subclasses whose __pow__
returns fractional values that int() would silently truncate to the right
integer. Custom nonintegral squares, even exact float9.0/Fraction(9), are
conservatively unsupported. Safe builtin/NumPy integer squares and integer zero
remain valid; native zero caused by a nonzero wrapped integer refuses.

## Consequences and limits

Only the integral derived-square domain tightens. Ordinary native float,
NumPy float and Fraction operations retain their prior results, warnings and
exceptions. Tiny floating square underflow can be harmless with the additive
one; no strict-positive-square requirement is introduced. Floating overflow,
general finite precision, mixed arithmetic and final nonfinite/zero integrity
remain separate open work, not certified by this repair. A wrapped negative
square previously reaching math.sqrt may now get the named refusal earlier.

No score cap, estimator/model, threshold, selector, accounting-v14, fingerprint,
generated record or frozen source/cohort change. Twelve knowingly wrong scalar
baseline rows intentionally become refusals; do not claim the old full baseline
hash is preserved or relabel historical outcomes.

## Verification and reversal

Record actual RED before runtime edits. Cover positive, negative and zero wraps,
signed/unsigned widths, safe square boundaries, integer zero, nonintegral custom
squares, guard precedence and native exceptions. Hypothesis compares native
integral squares with exact integer arithmetic. Preserve the other 48 baseline
scalar outcomes, all24 frontier reports and every prior runtime statement except
the import, square extraction/guard and corresponding return operand/docstring.
Independently review and run foreground make check-all before individual push
and exact CI verification. Restore the prior inline square to reverse, reopening
FINDING-283 without rewriting any historical evidence.
