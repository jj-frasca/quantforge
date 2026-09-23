# ADR-115: Bind each quality report to its bar symbol

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 9 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-043
- **Extends:** ADR-006's mandatory data-quality provenance gate

## Context

The quality engine accepts both a list of canonical bars and a separate report symbol. Canonical
bars validate their own symbols, but the engine never proves that the list is a single-symbol
series or that its identity matches the report. Pairwise financial checks are meaningless across
symbols, and a passing report must not describe different evidence from the bars later stored.

## Decision

At the start of `DataQualityEngine.check`, normalize the requested symbol with the same
strip-and-uppercase rule as `PriceBar` and `DataQualityReport`. For any non-empty input, require
the set of bar symbols to equal that single normalized symbol. Otherwise return a report containing
one `symbol_mismatch` error and run no time-series heuristics. `DataIngestionPipeline` retains its
existing fail-soft behavior: persist the failed report and do not store the bars.

The existing `insufficient_data` result remains authoritative for an empty list because there is
no contradictory bar identity to report. No heuristic threshold changes.

## Consequences

- A report's symbol is now bound to every bar it describes.
- Mixed or mislabeled series fail before cross-symbol returns can become plausible-looking quality
  evidence.
- Adapters with an identity bug produce an auditable failed report instead of contaminating storage.

## Reversal

Remove the early identity check. That would again allow the report label and stored-bar evidence to
diverge and is not recommended.
