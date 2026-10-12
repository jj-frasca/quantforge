# ADR-262: Preserve mixed native integer score order

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-211
- **Extends:** ADR-024, ADR-257, ADR-261

## Context

Mixed native integer/float columns and signed/unsigned integer columns can promote
into one float64 array before pandas ranking. Distinct represented scores become
false ties: int64 2**53+1 exceeds float64 2**53; uint64 2**63 exceeds int64 2**63-1.
Supplied-order tie resolution can reverse the portfolio legs and next-bar returns.
Homogeneous and extension integer panels already rank these values correctly.

## Options Considered

1. Use scalar-preserving object rank only for mixed native numeric dtype families.
   - Pro: retains represented integer/float order, existing true ties and formulas;
     homogeneous and extension inputs keep their current paths.
   - Con: object ranking also costs more for small mixed dtypes with no order loss.
2. Object-rank every integer-containing panel.
   - Pro: simple and correct on verified numeric inputs.
   - Con: unnecessarily slows homogeneous/nullable integers already handled correctly.
3. Scan values for loss or refuse large mixed integers.
   - Pro: could avoid the object cost for some callers.
   - Con: extra comparison/threshold machinery, or rejects supported finite scores.

## Decision

Retain ADR-261's wide floating branch. Also select object rank input when every
column is a native NumPy dtype of kind bool/signed-integer/unsigned-integer/float,
and its kind set includes signed-integer plus float, unsigned-integer plus float,
or signed-integer plus unsigned-integer. Use Python integer scalars and exact
represented float comparisons through pandas object rank, never integer-to-float
narrowing. Do not use value thresholds or Fraction conversion in production.

Keep existing quantile/infinity guards first, rank(method="first"), true supplied-
order ties, missing counts, weights, lag, costs and caller state unchanged.
Homogeneous, extension-only, existing object, complex and date inputs retain their
original path unless ADR-261 already selects wide-float ranking. Existing unsupported
inputs remain unsupported. No new dtype ban, coercion, score generator, threshold,
NumPy error-state or generated-record change.

## Consequences, identity and reversal

Finite public mixed native allocations change where numeric promotion fabricated
order. Small mixed dtype panels use the same object path even where their scores
would fit exactly; this bounded performance tradeoff avoids value-dependent rules.
All 16 shipped generators/45 configurations on canonical float64 prices retain the
original float64 rank path. This ranker is separate from longitudinal calibrated
search, so its accounting/search fingerprint is unchanged. No historical cohort
contamination or universal precision guarantee is inferred; already-rounded input
and arbitrary unsupported mixed payloads are outside this correction.

Observe RED for native signed/float, unsigned/float and signed/unsigned failures;
verify exact Fraction stable-order oracles, true ties/NaN, strict states and caller
nonmutation, empty, homogeneous/nullable/object compatibility and portfolio next-
bar behavior. Independent review and foreground make check-all precede individual
commit/push and exact CI. Remove only the mixed-native predicate to reverse this
correction while keeping ADR-261's wide branch; reopen FINDING-211.
