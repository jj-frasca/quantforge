# ADR-261: Preserve native wide floating score order

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-210
- **Extends:** ADR-024, ADR-257, ADR-260

## Context

Pandas' numeric DataFrame rank path narrows wide floating scores to float64.
Finite distinct longdouble values outside float64 range or separated below its
precision become fabricated ties. Supplied-order tie handling can then reverse
the intended legs and next-bar returns. ADR-260's infinity guard correctly accepts
the finite original observations and explicitly does not certify precision.

## Options Considered

1. Use existing pandas object ranking only when a native floating column is wider
   than float64.
   - Pro: retains native scalar comparisons, existing stable true ties and NaN
     exclusion with a small local change; ordinary inputs keep their exact path.
   - Con: object ranking is slower for these uncommon wide-input panels.
2. Replace the shared ranker with per-row native stable sorting.
   - Pro: explicit native-order control.
   - Con: adds loops, missing/mixed-dtype handling and performance risk to all callers.
3. Refuse all wide scores or only detect lost ordering.
   - Pro: avoids publishing the demonstrated wrong legs.
   - Con: discards supported finite inputs; detecting loss needs comparable ordering
     work without recovering the measured rank.

## Decision

After existing quantile and signed-infinity guards, select an object-typed rank
input only if a column has a native NumPy floating dtype wider than float64. Object
conversion must retain np.longdouble scalars, never convert them to Python float.
Apply the unchanged rank(axis=1, method="first") call to that selected input.
Use the original signals for valid counts and retain every weight, lag and cost
formula. Preserve actual native ties, NaN/pd.NA, mixed columns, empty panels,
caller state and ordinary float64/nullable/object/bool behavior. No score generator,
threshold, dtype ban, clipping or NumPy error-state change.

This changes finite public wide-input allocations where prior narrowing lost
order. It does not certify arbitrary precision or recover information already
rounded in a generator or DataFrame construction. Mixed integer/float narrowing
without a wide floating column remains a separate limitation.

## Consequences, identity and reversal

Canonical bars_to_frame converts prices to float64; independent checks of all 45
configurations across all 16 shipped generators on canonical float64 inputs produce
only float64 scores and keep the original path. The longitudinal calibrated search
and its panel-null adapter do not use this ranker. Existing calibration identities
and generated evidence therefore remain unchanged; this is not new Type-I or power
evidence for wide factors, and no historical contamination is inferred.

Observe failing wide-order tests before code. Verify native-scalar stable-order
oracles including signed extremes, near-one/subnormal separation, true ties,
missing/empty/mixed panels and next-bar portfolio returns; preserve ordinary exact
baselines and generators with independent review. Run foreground make check-all,
then immediate individual delivery and exact CI. Reversal removes the conditional
rank-input selection and reopens FINDING-210; valid wide ordering becomes lost again.
