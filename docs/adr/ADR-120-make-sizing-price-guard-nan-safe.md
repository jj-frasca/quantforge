# ADR-120: Make the sizing price guard NaN-safe

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-048

## Context

`equal_weight_targets` (`app/execution/sizing.py`) uses two different comparisons against the same
`price` field: `q.price > 0.0` to count active names, and `q.price <= 0.0` to decide whether a
single quote degrades to a flat (zero) target. Both are `False` for `price = nan`, so a NaN-priced
quote silently skips the flat guard and reaches `int(target_dollars / q.price)`, which raises
`ValueError` and aborts the entire call rather than degrading just that one symbol.

## Options Considered

1. **Use the same non-positive predicate, inverted, in both places (`not q.price > 0.0`).**
   - Pro: one predicate, impossible for the two checks to disagree on NaN or anything else again.
     No new import, no behavior change for any price that was already handled correctly.
   - Con: `not x > 0.0` reads slightly less directly than an explicit `math.isnan(x) or x <= 0.0`.
2. **Add an explicit `math.isnan` check alongside `<= 0.0`.**
   - Pro: arguably more self-documenting about which case it's guarding.
   - Con: two predicates to keep in sync is exactly the shape of bug this ADR fixes; a future edit
     to one side and not the other reintroduces the same class of defect.
3. **Validate `price` at the `PositionQuote` boundary (Pydantic field validator rejecting NaN).**
   - Pro: fails fast at construction instead of at sizing time.
   - Con: larger blast radius for a pure-math sizing function whose own docstring already documents
     "non-positive price is flat" as the intended degrade-not-crash behavior; a boundary-reject
     would change that contract rather than fix the internal inconsistency.

Chose option 1: mirror the active-count predicate exactly (negate it) so both branches are
definitionally the same comparison.

## Decision

`equal_weight_targets`'s per-quote skip-to-flat check changes from `q.price <= 0.0` to
`not q.price > 0.0`, matching the active-count predicate's polarity exactly. A NaN price, like a
zero or negative price, now degrades that one quote to a `target_qty=0` and frees its slice for the
other active names, instead of raising and aborting the whole book.

## Consequences

- `equal_weight_targets` cannot raise on a NaN-priced quote; it degrades per-symbol, matching its
  own documented "non-positive price yields a 0 target" contract.
- No behavior change for any price that was already `> 0.0`, `== 0.0`, or negative.

## Reversal

Revert the single comparison back to `q.price <= 0.0`. Not recommended — that reintroduces
FINDING-048's crash path for any NaN-priced quote.
