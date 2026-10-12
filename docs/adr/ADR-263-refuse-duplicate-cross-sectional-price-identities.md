# ADR-263: Refuse duplicate cross-sectional price identities

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-212
- **Extends:** ADR-024, ADR-254, ADR-255, ADR-259
- **Relates to:** ADR-149

## Context

Unique ranked signals can project onto repeated price column labels. The same
symbol's weight is copied onto every occurrence, doubling one portfolio leg and
its fees while publishing a finite return under the dollar-neutral contract.
ADR-259 validates membership but deliberately left duplicate identity separate.
Canonical dict-based panel construction supplies unique symbols; direct public
asset/portfolio kernels have no intrinsic duplicate price-column guard.

## Options Considered

1. Refuse duplicate original price columns at the shared asset_returns boundary.
   - Pro: prevents publication from ambiguous symbol evidence in direct asset and
     portfolio callers, retaining the existing validation order.
   - Con: malformed direct callers must correct their source metadata.
2. Add only a portfolio-entry guard before ranking.
   - Pro: fails earlier for portfolio callers.
   - Con: leaves direct asset returns ambiguous and changes existing error precedence.
3. Deduplicate, aggregate or normalize column labels.
   - Pro: may permit computation to continue.
   - Con: chooses or invents symbol evidence, changes weights, fees or universe order.

## Decision

At asset_returns entry, after the existing unique ascending calendar check and
before populated price validation/pct_change, require prices.columns.is_unique.
Refuse duplicates with ValueError, including axes with zero rows and repeated
string, integer, missing or tuple/MultiIndex labels. Empty zero-column axes are
vacuously unique. This is intrinsic source identity; do not sort, deduplicate,
normalize labels or choose a repeated price series.

Preserve original unique labels/order/dtypes, unique empty/singleton panels and
all native return/rank/projection/lag/cost formulas. Keep calendar refusal first;
portfolio cost/quantile/membership validation and weight construction stay in their
existing positions. Preventing publication does not promise refusal before ranking.
No complete-universe, label-type, signal-duplicate, timezone/cadence, estimator,
threshold, NumPy error-state or generated-record policy is added.

## Consequences, identity and reversal

Duplicate source metadata can no longer multiply one ranked position during
projection or masquerade as distinct asset-return evidence, even with zero exposure.
Valid zero-cell panels remain supported; duplicate zero-row axes are refused as
malformed identity rather than receiving a special metadata exception. Production
price_panel_from_frames constructs unique dict-key columns and frozen forward
universes are unique under ADR-149. No historical contamination is inferred.
Longitudinal calibrated search is separate and its accounting identity is unchanged.

Observe duplicate-identity RED before code, including doubled-leg accounting,
flat/singleton/empty histories, mixed label types and refusal before source arithmetic.
Verify calendar/cost/membership precedence, unique arbitrary labels/MultiIndex/order,
zero-cell/native dtype behavior and caller nonmutation, an adversarial Hypothesis
portfolio invariant, independent review and foreground make check-all. Deliver one
commit immediately and watch exact CI. Remove only the column-uniqueness guard to
reverse this correction and reopen FINDING-212.
