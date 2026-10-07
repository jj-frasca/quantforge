# ADR-190: Validate shared DSR trial accounting

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-125
- **Extends:** ADR-046, ADR-050, ADR-054

## Context

Probability DSR accepts nonpositive trial counts or dispersion and produces an ordinary unpenalized
probability. The expected-max helper's <=1 shortcut bypasses count/dispersion validity; margin DSR
has only weak sign checks that the probability wrapper bypasses. Direct production callers supply
positive integer lifetime counts and robust positive real dispersion. No invalid contract is intended.

## Options Considered

1. Validate at expected_max_sharpe, the shared multiplicity primitive, before its N=1 shortcut.
2. Add separate wrapper guards. Risks drift while direct expected-max calls remain unprotected.
3. Clamp invalid inputs to one trial or zero dispersion. Invents unpenalized evidence.

## Decision

Require a positive nonboolean numbers.Integral trial count and normalize it to Python int. Require
positive finite float-representable nonboolean numbers.Real dispersion and normalize it to float.
Apply both checks in expected_max_sharpe before the one-trial no-haircut shortcut. Remove the
margin wrapper's duplicate weak sign checks; both wrappers delegate to the shared complete guard.
Reject malformed counts/dispersion with ValueError. Preserve N=1 zero haircut for valid dispersion,
native expected-max quantile/scale arithmetic, nonnegative haircut clamp and all PSR formulas.

## Consequences and limits

Invalid accounting cannot yield unpenalized margin/probability values. RED tests cover all three
public entry points, shortcut bypasses and invalid scalar types. Valid Python/numpy integral counts,
numpy/Fraction real dispersion and ordinary one/many-trial oracle behavior remain. Whole-search
probability's existing ValueError-to-unmeasured policy is unchanged; valid production counts and
robust dispersion continue to pass. No estimator, threshold, trial accounting identity, calibration
procedure or generated data changes. FINDING-126 separately records large-count quantile rounding
and finite derived-haircut overflow; this source boundary does not claim to fix them.

## Reversal

Remove the shared input checks and restore duplicate margin sign checks. This reopens FINDING-125.
