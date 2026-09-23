# ADR-113: Add the corporate_action discontinuity check to DataQualityEngine

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session #101 (delegated authority, AUTONOMY_CHARTER.md §1)

## Context
`data-contracts.md` §5 documents 8 quality checks; check #3, `corporate_action`, is specified
("price discontinuity suggesting delisting/merger/remap — gap > 50% not explained by
adj_factor") but was never implemented — `DataQualityEngine` has run only 6 of the 8 checks
plus `insufficient_data` since the engine was built (ADR-006). ARCHITECTURE.md §0.6 lists it
under "DEFERRED / NOT YET BUILT" alongside `vendor_cross_validation` (#8), but unlike #8 this
one needs no second vendor — every input it needs (`close`, `adj_factor`) is already on
`PriceBar`. There is no reason left to defer it.

`PriceBar.close` is already split/dividend-adjusted at ingestion (`adj_factor` is cumulative
and pre-applied — see `price_bar.py`'s docstring and `data-contracts.md`'s field table). This
matters for the check's design: a *real* split or dividend does not show up as a close
discontinuity (the historical close was already smoothed), it shows up as an `adj_factor`
jump between consecutive bars — which is exactly what `split_dividend_consistency` (check #2)
already flags. So a large *close* discontinuity that is **not** paired with a corresponding
`adj_factor` jump is not a normal corporate action already captured by check #2 — it is
something check #2 cannot explain: a delisting, merger, ticker remap, or vendor data error.
That is the gap this check fills.

## Options Considered
1. **New independent check: unexplained close gap > 50%, `adj_factor` ratio unchanged.**
   - Pro: matches the documented contract exactly; reuses the existing `adj_factor_low`/
     `adj_factor_high` bounds from check #2 to define "unchanged," so the two checks stay
     consistent by construction (whatever #2 would flag as a split, #3 treats as explained).
   - Con: two thresholds (50% price gap, [0.5, 2.0] adj_factor band) now have to be read
     together to understand either check fully — a small cross-check coupling.
2. **Fold this into `price_anomaly` (check #5) as a higher-severity tier.**
   - Pro: one check instead of two; no new config fields.
   - Con: conflates two different questions — #5 is "is this move large," #3 is "is this move
     *explained*." A 25% earnings-gap move and a 90% delisting gap are both ">20%" but only the
     second is a corporate-action signal; merging them would either weaken #5's existing
     threshold semantics or bury the more specific signal inside a generic one. Also contradicts
     the already-published, separately-numbered check in `data-contracts.md` §5.
3. **Defer until a second vendor exists (treat it like #8).**
   - Pro: a corroborating vendor could distinguish "real discontinuity" from "bad print" with
     more confidence.
   - Con: unlike #8, this check's definition never required a second vendor — it is a
     single-series heuristic like #2/#5/#6, and it's already been documented as such since the
     contract was written. Deferring it further has no methodological justification, just
     inertia; per the charter, "backlog empty" is not true while a documented, buildable check
     sits unbuilt.

## Decision
Implement check #3 as `DataQualityEngine._corporate_action`, run alongside the other five
heuristic checks in `.check()`. For each consecutive bar pair: if `abs(close_ratio - 1) >
corporate_action_pct` (default `0.50`, i.e. a >50% single-bar move) **and** the `adj_factor`
ratio between the same pair falls *inside* `[adj_factor_low, adj_factor_high]` (the existing
check #2 bounds — meaning check #2 would NOT flag this pair as a split/dividend jump), emit a
`corporate_action` warning. If the `adj_factor` ratio is *outside* those bounds, the move is
already explained by check #2 and `corporate_action` does not also fire for that pair — the
two checks partition "large, adj_factor-explained" from "large, adj_factor-unexplained" rather
than overlapping. `corporate_action` does not suppress or replace `price_anomaly` (check #5,
20% default threshold) — a >50% unexplained gap legitimately triggers both; they answer
different questions ("is this large" vs "is this an unexplained discontinuity") and a
consumer of `DataQualityReport` may care about either independently. New `QualityConfig` field:
`corporate_action_pct: Decimal = Decimal("0.50")`, tunable like every other threshold. Warning
severity, not error — like every other heuristic check, this flags a potential issue for
review; it does not block the gate or claim to identify the cause (CLAUDE.md rule 6, backend
Python conventions' "data-quality honesty" rule).

## Consequences
- `data-contracts.md` §5's "Build status" line changes from "implemented today = #1, #2, #4,
  #5, #6" to include #3; only #8 (`vendor_cross_validation`) remains genuinely blocked on the
  Polygon adapter (Phase 3+).
- `ARCHITECTURE.md` §0.6's "Active `DataQualityEngine` checks" list gains `corporate_action`.
- A symbol with a real, large, unexplained price discontinuity (e.g. a bad print, or a
  ticker-remap the adapter didn't catch) now surfaces a specifically-named warning instead of
  only the generic `price_anomaly` warning — a downstream consumer (or a future dashboard) can
  now distinguish "big move" from "big, unexplained move" without re-deriving the adj_factor
  cross-check itself.
- Coupling: `corporate_action`'s "explained" branch depends on check #2's threshold constants
  (`adj_factor_low`/`adj_factor_high`). If a future ADR changes those bounds, it changes what
  `corporate_action` considers "explained" too — this is intentional (the two checks must stay
  consistent) but means check #2's config comment should note the dependency.
- Reversible: delete `_corporate_action`, its call in `.check()`, the `corporate_action_pct`
  config field, and its tests; revert the two doc lines above. No stored data or migration is
  affected — this is a pure heuristic over already-stored fields.
