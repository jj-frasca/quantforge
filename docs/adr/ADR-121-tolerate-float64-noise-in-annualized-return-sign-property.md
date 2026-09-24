# ADR-121: Tolerate the float64 noise floor in the annualized-return sign property

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-049

## Context

`test_annualized_return_has_compounded_total_return_sign` (ADR-110) asserts that
`annualized_return` and `total_return` always share a sign, since both are monotone, sign-preserving
transforms of the same compounded log-growth sum. That is true in exact arithmetic. It is not always
representable in float64: the two quantities apply different scale factors
(`1` vs `TRADING_DAYS / len(returns)`) to the same tiny log-growth sum before exponentiating, so one
side's exponent can round to exactly zero growth while the other's crosses float64's epsilon and
rounds to a nonzero residue. Hypothesis found this at `returns=[0.0, 6.75e-18]`: `total_return ==
0.0` exactly, `annualized_return == 8.88e-16` — a real sign disagreement, but one confined entirely
to a magnitude (~1e-16) that is meaningless next to any real strategy's return (routinely 1e-4 or
larger).

## Options Considered

1. **Skip only the double-negligible case with `hypothesis.assume`, keep the exact sign assertion
   otherwise.** `assume(abs(total_return) > 1e-9 or abs(annualized_return) > 1e-9)` before the
   assertion — the property still runs, and still catches any case where at least one side is
   meaningfully nonzero.
   - Pro: narrowest possible carve-out; a real sign-reversal bug where either metric is actually
     material still fails the test. No change to production code, which is already correct.
   - Con: an arbitrary-looking threshold constant in the test.
2. **Loosen the assertion itself to a tolerance-based comparison** (e.g. compare rounded values).
   - Con: changes the property's shape for every input, not just the boundary case; harder to see
     at a glance that the assertion is still meaningful for real magnitudes.
3. **Change `total_return`/`annualized_return` to round sub-epsilon growth to exactly zero before
   returning.** Would make the two functions agree at the boundary by construction.
   - Con: production code is not wrong today — rounding it introduces an arbitrary threshold into
     the metrics themselves (which real callers never notice this deep in the noise floor) purely
     to satisfy a test; the test is the right place to express "this deep in the noise, I don't
     care," not the metric.

Chose option 1: `assume()` is Hypothesis's idiomatic way to declare an input outside a property's
intended domain, and 1e-9 is nine orders of magnitude above where any real backtest return lives,
so it cannot hide a real sign-reversal defect.

## Decision

Add `assume(abs(metrics.total_return) > 1e-9 or abs(metrics.annualized_return) > 1e-9)` immediately
before the sign assertion in `test_annualized_return_has_compounded_total_return_sign`. No
production code changes — `metrics.py`'s `total_return`/`annualized_return` are unchanged.

## Consequences

- The property test no longer fails on Hypothesis-generated inputs whose true compounded return is
  representable as exactly zero on one scale and as float64 noise on the other.
- The property still holds, and is still checked, for every input where either metric is materially
  nonzero — a real sign-reversal bug remains caught.
- `.hypothesis/`'s local example cache (gitignored) will stop replaying this input as a failure on
  this machine once this commit lands.

## Reversal

Remove the `assume` line. Not recommended — reintroduces a test that fails nondeterministically
(only once Hypothesis's random search happens to draw a sub-epsilon example) on a mathematically
correct implementation.
