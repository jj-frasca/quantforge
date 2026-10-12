# ADR-255: Require causal cross-sectional source calendars

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-204
- **Extends:** ADR-024, ADR-176, ADR-254

## Context

Cross-sectional returns and holdings use positional lags. Direct raw panels with
reordered timestamps let earlier performance consume future prices and signals.
Duplicate timestamps give ambiguous row identity while still producing finite
portfolio returns. ResearchDataset protects production inputs but is not required
by the public asset/portfolio kernels.

## Options Considered

1. Require unique ascending source indexes at the shared return boundary.
   - Pro: reuses ADR-176's causal source policy without changing supplied evidence.
   - Con: checks index identity/order on each return computation.
2. Sort or deduplicate the source.
   - Pro: could permit computation to continue.
   - Con: silently alters row order or chooses between contradictory observations.
3. Trust production preparation only.
   - Pro: no kernel check.
   - Con: direct callers still publish noncausal positional results.

## Decision

At asset_returns entry require prices.index.is_unique and
prices.index.is_monotonic_increasing before original-price validation or pct_change.
Refuse invalid calendars with ValueError. Preserve the original frame and every
native return, rank, lag, cost and signal operation. Do not sort, deduplicate,
require DatetimeIndex/UTC or impose daily cadence. Ordered generic, naive, aware,
empty and singleton calendars remain supported.

portfolio_returns constructs weights before calling this shared boundary; this
decision prevents publishing invalid-calendar returns without adding a broader
signal-alignment policy. Source order alone does not certify a strategy's causality.

## Consequences and reversal

A cross-sectional positional lag cannot silently cross backward through source
timestamps. Valid canonical prices retain exact results, acquisition and thresholds.
No estimator, schema, broker action or generated record changes. Remove the index
guard to reverse this correction and reopen FINDING-204.
