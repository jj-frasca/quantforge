# FINDING-046: Quality reports do not bind calendar uniqueness or adapter source

- **Severity:** High
- **Status:** Resolved by ADR-118
- **Found:** 2026-09-23, Codex autonomous session 10
- **Affects:** `DataQualityEngine`, `DataIngestionPipeline`, canonical price-bar storage (ADR-006)

## Finding

ADR-115 binds a quality report to its bar symbol, but the same boundary still accepts duplicate
`timestamp_utc` values and bars whose `source` differs from the adapter that produced the series.
A same-symbol mixture of `yfinance` and `alpaca` bars therefore receives a passing report. The
production repository stores `(symbol, timestamp_utc, source)` as its primary key and reads without
a source filter, so mixed vendors become multiple rows at one calendar instant. A duplicate from
one source is instead silently collapsed by `Session.merge`, while the in-memory repository keeps
both rows. The report can consequently describe a different effective series depending on the
repository implementation.

This is not hypothetical: the backtest trade-marker helper and its regression explicitly document
that real yfinance data has reached downstream code with a duplicated timestamp. Handling a
non-unique research index without crashing does not make the input evidence valid.

Pairwise missing-bar, anomaly, stale-price, split, and corporate-action heuristics assume one
ordered observation per calendar instant from one named adapter. Running them across duplicates or
mixed vendors produces plausible-looking results over a series that has no single provenance or
well-defined return path.

## Required correction

Before any heuristic check, require unique timestamps and exactly one source equal to the ingestion
adapter's declared source. Emit one structural error per violated dimension and return without
pairwise checks. The ingestion pipeline must pass the adapter source into the quality boundary,
persist the failed report, and store no bars. Empty input remains governed by
`insufficient_data`; no heuristic threshold changes.
