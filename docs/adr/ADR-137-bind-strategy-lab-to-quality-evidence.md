# ADR-137: Bind StrategyLab claims to quality-checked evidence

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-068
- **Extends:** ADR-006, ADR-014, ADR-016, and ADR-136

## Context

The single-name research pool is the project's durable claim surface, but its production frame
providers call market-data adapters directly. `ExperimentManifest` exists only in tests, and
`Experiment` cannot retain either the report created by the mandatory quality gate or the report UUID
made canonical by ADR-136. A report UUID alone is also insufficient when the corresponding evidence
is not durable beside the generated research record.

## Options Considered

1. **Carry one quality-checked dataset object into StrategyLab and persist its evidence.**
   - Pro: makes the quality gate and lineage structural inputs to a real-data search; the pool remains
     self-contained when no TimescaleDB is available on a cloud runner.
   - Con: production hunt providers must return metadata as well as a DataFrame, and legacy rows need
     nullable compatibility fields.
2. **Look up the latest report after a search.**
   - Pro: smaller change to the hunt interface.
   - Con: report rows do not identify the exact bars used, concurrent or overlapping ingests can race,
     and the lookup would invent lineage after computation.
3. **Populate only the UUID and leave acquisition unchanged.**
   - Pro: fills the manifest field.
   - Con: the search would still bypass ADR-006 and the UUID could point to unrelated evidence.

## Decision

Introduce an immutable real-data research dataset containing the canonical frame, passed
`DataQualityReport`, source, adapter version, requested half-open range, and executed git revision.
The construction boundary runs `DataQualityEngine` on the fetched bars and refuses failed evidence.
Single-name production hunts consume this object, then persist both the complete report and an
`ExperimentManifest` derived from the selected trial. The manifest and experiment share one UUID;
its `data_quality_report_id`, symbol, source, adapter version, and dates must agree with the embedded
dataset evidence. Existing pool rows retain nullable lineage instead of receiving guessed links.
Synthetic null/power calibration may continue to call `run_search` directly because it is generated
evidence, not vendor acquisition.

## Consequences

- New scheduled single-name experiments prove which quality check, vendor implementation, request
  window, code revision, selected strategy, and gate configuration produced the claim.
- A failed quality report stops the search before any trial or pool write.
- Cloud runners need no database solely to preserve quality evidence; the complete report travels in
  the partitioned experiment record and its UUID remains the manifest link.
- Historical rows remain readable but explicitly lack the new lineage.
- Cross-sectional research has a different panel identity and requires a separate decision before
  adopting this single-symbol manifest shape.

## Reversal

Remove the dataset boundary and nullable experiment lineage fields. This would restore direct,
un-audited vendor frames and is not recommended.
