# FINDING-043: Quality report does not bind bar symbols

- **Severity:** High
- **Status:** Resolved by ADR-115
- **Found:** 2026-09-23, Codex autonomous session 9
- **Affects:** Data-quality provenance and ingestion storage gate

## Finding

`DataQualityEngine.check(bars, symbol)` writes the caller-provided `symbol` into its report but
never verifies that every `PriceBar.symbol` matches it. A complete AAPL series can therefore
produce a passing report labelled MSFT, and a mixed-symbol list can be compared pairwise as though
it were one time series. `DataIngestionPipeline` then persists that passing report and stores the
mislabeled or mixed bars.

This breaks ADR-006's promise that each ingested series has a reproducible quality snapshot: the
report identity is not bound to the evidence it evaluated, and cross-symbol close moves can be
misclassified as data anomalies rather than rejected as structurally invalid input.

## Required correction

Normalize the requested report symbol and require every non-empty input bar to carry that exact
symbol before running pairwise heuristics. On mismatch, emit a structural `symbol_mismatch` error
and return immediately so the ingestion gate persists the failed report but stores no bars. Add
engine and pipeline regressions for a mislabeled series. Do not change heuristic thresholds.
