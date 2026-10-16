# ADR-298: Refuse unmeasurable native MinBTL arithmetic

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 21, ISO 2026-W42
- **Resolves:** FINDING-252
- **Extends:** ADR-015/016/295/297

## Context

Original valid positive Sharpe operands can overflow or underflow their native
square, or wrap in fixed-width integer arithmetic. FINDING-252 records a NumPy
float64 score of 1e160 producing zero required years instead of a representable
nonzero subnormal, and a wrapped integer square producing an incorrect positive
requirement. A finite-positive denominator check alone misses positive integer wrap.
Normal gate reports supply Python floats, whose extreme squaring instead raises
or leads to infinite division. No production false graduate or changed rate is
established by these standalone synthetic counterexamples.

## Options considered

1. Refuse unmeasurable native arithmetic: small, preserves ordinary calculation
   and needs no new estimator; deliberately declines some recoverable cases.
2. Reorder or scale the formula: could recover representable extreme answers,
   but changes rounding and needs a separately certified numerical design.
3. Accept finite outputs regardless of intermediate integrity: simplest but
   permits wrapped positive integers and overflow-derived zero requirements.
4. Float-normalize every original score: removes integer wrapping but changes
   accepted Fraction/NumPy semantics and does not alone fix square overflow.

## Decision

After the existing source guard and nonpositive-Sharpe infinity shortcut, compute
the unchanged native numerator, then native square. Inspect the square as a Python
float: it must be finite and strictly positive. Retain the original square for
subsequent division. For an original Integral score, also require its native square
converted to Python int to equal the independent mathematical Python-int square.
This catches positive, zero and negative fixed-width wrap without replacing safe
native squares. Keep math.log on the normalized Python trial count, including
counts too large to convert to float.

Divide the original numerator by the original validated square, and require a
finite float-representable, originally nonnegative result. Return the original
result. Convert native OverflowError, ZeroDivisionError and FloatingPointError
into ValueError. Use no NumPy error-state context or warning filter: preserve the
caller's policy and warnings. No N=1 shortcut; an invalid square still refuses
when the mathematical requirement would be zero. A valid square retains the
existing zero result at N=1. Finite nonpositive original scores retain infinity.

Binary64 inspection deliberately refuses native finite squares above its maximum
or below its smallest positive representable range, including wider-floating and
exact Fraction values. This is a representation-domain refusal, not a claim that
those mathematical squares are nonfinite. Ordinary supported native operations
retain their order and exact result; universal precision or correct rounding is
not certified. No clipping, score cap, scaling recovery, denominator floor,
threshold, GateConfig hash, accounting-v14 or production calibration change.

## Consequences, verification and reversal

Invalid intermediate or result evidence cannot become a numeric requirement.
Some mathematically recoverable extreme cases now explicitly refuse. TDD must
cover square overflow/underflow, quotient overflow, positive/negative/zero integer
wrap, safe integer boundary squares, N=1 precedence, Fraction/native preservation,
huge Python trial counts and caller ignore/warn/raise policies. Hypothesis checks
safe versus wrapped integral squares and unchanged native finite results.
Independent review and foreground make check-all precede individual delivery.

Restore the prior one-expression kernel to reverse, reopening FINDING-252.
Historical scores, frozen cohorts and generated records remain untouched; no
remeasurement or retrospective corruption claim is made.
