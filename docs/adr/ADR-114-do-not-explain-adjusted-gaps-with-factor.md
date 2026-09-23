# ADR-114: Do not explain adjusted-price gaps with the applied factor

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 9 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-042
- **Supersedes in part:** ADR-113's partition between checks 2 and 3

## Context

`OHLCVNormalizer` stores `PriceBar.close` as the vendor's adjusted close and applies
`adj_factor = adj_close / raw_close` to the other OHLC fields. ADR-113 nevertheless treats a large
factor change as an explanation for a simultaneous large canonical-close move. That would be true
for an unadjusted close, but the canonical close has already removed the split/dividend effect.

## Decision

`corporate_action` evaluates only the absolute consecutive move in canonical adjusted closes. A
move strictly above `corporate_action_pct` emits its warning whether or not the adjustment factor
also changes. `split_dividend_consistency` continues to evaluate the factor independently, so one
bar pair may legitimately emit both warnings. Warning severity, the 50% default, and every other
quality threshold remain unchanged.

## Consequences

- A factor change cannot hide a discontinuity that survives adjustment.
- Simultaneous warnings communicate two distinct observations: factor discontinuity and adjusted
  price discontinuity. Neither warning claims the cause is proven.
- The checks no longer partition events, matching the canonical schema's already-adjusted price
  contract.

## Reversal

Restore the factor-based suppression. That would again interpret an already-applied adjustment as
an explanation for residual adjusted-price movement and is not recommended.
