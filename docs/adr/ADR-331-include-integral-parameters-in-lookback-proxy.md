# ADR-331: Include Integral parameters in the lookback proxy

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 8, ISO 2026-W43
- **Resolves:** FINDING-278
- **Extends:** ADR-039/330

## Context

lookback_embargo includes Python int parameters but silently ignores NumPy
integer scalars. Two valid SMA grids with identical signals can consequently
receive embargo 60 versus embargo 2 and different accepted PCV means. ADR-198
cannot identify an omitted lookback: the supplied folds honor the smaller
declared embargo. No production occurrence or false graduate is established.

## Options Considered

1. Include original nonboolean numbers.Integral parameters and normalize their
   values before max. Supports equivalent discrete evidence, with deliberately
   changed diagnostics for formerly omitted parameters.
2. Reject non-Python parameter values. Less permissive, but changes otherwise
   accepted strategy and signal domains rather than correcting this helper.
3. Keep ignoring them. Avoids a compatibility change but contradicts the proxy's
   largest-integer-parameter definition for valid integral strategies.

## Decision

Change only the list's integer predicate from int to Integral and its retained
value to int(value). Preserve the explicit bool exclusion, floor guard, parameter
iteration and max expression. Other parameter types remain ignored: this is not
a validator for arbitrary strategy parameters. Keep negative integer/max-floor
behavior and the original floor operand. No factory coercion, signal, default,
fold formula, scorer, selection, gate, threshold or schema changes.

## Consequences and limits

An integral strategy parameter cannot vanish merely because its scalar class
is NumPy's. Maximal unsigned helper inputs normalize without wrapping, although
the accepted engine witness is signed int64; a uint64 SMA probe fails in pandas
rolling and supplies no accepted producer evidence. This remains a parameter
proxy, not a certified dependency graph or guarantee of source isolation,
independence, PIT availability or causal purged selection. FINDING-272's rolling
numerical-history caveat remains authoritative.

Longitudinal search invokes ValidationEngine and calibration invokes that search;
the helper is on their call path. No caller absence is claimed. The shipped
coarse/default-centered refinement inventory covers 34 families, 68 grids and 1,360 configs,
with only native int/float parameters and identical old/proposed embargo values.
Normal native-input arithmetic and accounting-v14 remain; custom formerly omitted
integral-parameter executions deliberately change. No new calibration rate or
remeasurement is claimed; historical/generated/frozen records remain untouched.

## Verification and reversal

Observe helper and actual ValidationEngine typed-equivalence RED before runtime
edits. Hypothesis checks the largest original Integral parameter with floor,
mixed ignored types and signed/unsigned families. Verify max values and unchanged
floor/float/bool behavior. Preserve 204 frozen native catalog/floor payloads and
all module AST outside the two list changes and helper docstring. Independent
review, foreground make check-all and individual push/exact CI are required.
Reverse the predicate/value conversion to restore the omission; retain the
finding and never rewrite earlier diagnostic records.
