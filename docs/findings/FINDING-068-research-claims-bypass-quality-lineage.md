# FINDING-068: Research claims bypass quality-report lineage

- **Severity:** High
- **Status:** Resolved by ADR-137
- **Found:** 2026-09-27, Codex autonomous session 28
- **Affects:** single-name StrategyLab acquisition, `Experiment`, `ExperimentManifest`

## Finding

ADR-006 requires every research claim to use quality-gated data and link the persisted quality
snapshot from `ExperimentManifest`. ADR-136 made that link technically available, but no production
path constructs an `ExperimentManifest`: every constructor is in a test. The scheduled and sharded
single-name hunts call `DataSourceAdapter.fetch_price_bars`, convert the returned bars directly to a
DataFrame, and persist an `Experiment` that contains neither the quality report nor its id.

Consequently, malformed but model-valid vendor data can reach the search without the structural and
heuristic quality preflight, and a durable pool row cannot identify which quality evidence supported
its prices. `ExperimentManifest.data_quality_report_id` remains dead lineage despite the canonical
UUID introduced by ADR-136.

## Required correction

Make real-data StrategyLab inputs carry a passed `DataQualityReport` together with the exact source,
adapter version, request range, and executed code revision. Persist that report inside the research
record and attach an `ExperimentManifest` whose report id and experiment id agree with the embedded
evidence. Fail before search when the report rejects the bars or any identity dimension drifts.
Legacy pool rows remain readable with explicit null lineage; synthetic calibration stays a separate,
non-vendor procedure and must not receive invented quality evidence.
