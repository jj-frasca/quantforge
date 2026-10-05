# ADR-176: Require causal backtest price calendars

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** Codex autonomous session 1, ISO 2026-W41
- **Resolves:** FINDING-108
- **Extends:** ADR-007

## Context

The engine's lag is positional. Without unique ascending prices, yesterday's position can belong
to a later timestamp, violating the causal contract before any validation method is applied.

## Options Considered

1. Reject malformed source calendar identity at the engine boundary. This preserves supplied
   evidence and makes the lag causal for every direct caller.
2. Sort or deduplicate. This silently changes execution order or chooses among contradictory rows.
3. Rely on ResearchDataset preparation. Public Series/frame callers can bypass that boundary.

## Decision

Before calculating returns or reindexing signals, require `prices.index.is_unique` and
`prices.index.is_monotonic_increasing`. Reject invalid calendars with ValueError. Do not sort,
deduplicate, require UTC/DatetimeIndex, or change signal reindex/clip/fill, lag, turnover, costs,
metrics, or capital behavior. Empty/single-row ordered indexes retain their existing semantics.

## Consequences and limits

A positional one-row lag now respects the supplied source index's strict ordering. This blocks
malformed direct engine inputs while leaving canonical production frames unchanged. Ordered
generic or naive indexes remain accepted; index order alone does not certify source provenance,
actual daily cadence, price validity, or strategy causality. The signal generator may still have
its own look-ahead defects; this guard only makes execution order honest.
No validation estimator, threshold, generated data or workflow changes.

## Reversal

Remove the source-index guard. This reopens FINDING-108.
