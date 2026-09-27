# FINDING-069: Cross-sectional claims bypass quality lineage

- **Severity:** High — a durable multi-symbol graduation claim can be produced from unchecked
  vendor frames with no recoverable identity for any contributing series
- **Status:** Resolved by ADR-138
- **Date:** 2026-09-27
- **Affects:** cross-sectional hunt acquisition, `CrossSectionalExperiment`, ADR-024

## Finding

ADR-137 deliberately fixed only the single-name StrategyLab boundary because
`ExperimentManifest` describes one symbol. The production cross-sectional driver still fetches
every symbol directly from `YFinanceAdapter`, converts bars to frames, and passes those frames into
the panel search without `DataQualityEngine`. Its durable experiment records the surviving symbol
names but no quality reports, adapter version, request ranges, executed revision, or report UUIDs.

Per-symbol failures are resiliently skipped, which is appropriate for an unreliable universe
fetch, but a successfully normalized series can still contain a quality-gate error and enter the
shared panel. After short-history and common-calendar filtering, the stored claim cannot prove
which exact per-symbol evidence formed that panel. A single-symbol manifest cannot honestly encode
this relationship because one cross-sectional return series depends jointly on every retained
column.

## Required correction

Make the production hunt consume quality-checked `ResearchDataset` values, preserve evidence only
for the symbols that survive panel construction, and store a panel-specific manifest whose
component list binds each retained symbol to its source, adapter version, requested range, and
quality-report UUID. The manifest must also bind the selected strategy/parameters, gate config,
experiment identity, and executed git revision. Historical and synthetic experiments must remain
readable with explicitly absent lineage.
