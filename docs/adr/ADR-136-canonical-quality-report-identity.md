# ADR-136: Make quality-report identity canonical before persistence

- **Status:** Accepted
- **Date:** 2026-09-26
- **Deciders:** Codex autonomous session 26 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-067
- **Extends:** ADR-006 and ADR-135

## Context

`ExperimentManifest.data_quality_report_id` is intended to identify the persisted quality snapshot
behind a research claim. Today only the TimescaleDB insert creates that UUID, and the repository
immediately loses it. The canonical report returned by ingestion cannot name its own durable row.

## Options Considered

1. **Create the UUID on `DataQualityReport` and persist it unchanged.**
   - Pro: one identity exists before, during, and after persistence; every repository and API sees
     the same value without a storage-specific return channel.
   - Con: API responses gain one field.
2. **Return a generated UUID from `save_quality_report`.**
   - Con: splits one report across model and storage identities and requires a separate result
     field or model copy after every save.
3. **Look up the latest report by symbol and timestamp.**
   - Con: races concurrent ingestion, relies on non-unique fields, and cannot prove exact identity.

## Decision

Add `id: UUID` with a UUID4 default factory to `DataQualityReport`. Repositories retain the report
unchanged and TimescaleDB uses `report.id` as the row primary key. Ingestion and HTTP responses
already carry the canonical report, so its durable identity remains available for
`ExperimentManifest.data_quality_report_id`. Existing constructors need no call-site change.

## Consequences

- A report has one stable identity across quality checking, persistence, API serialization, and
  experiment lineage.
- Re-saving the same report to TimescaleDB conflicts on its primary key instead of silently
  creating two identities; callers must create a new report for a new quality run.
- Historical rows and manifests are unchanged; no link is guessed retroactively.
- No quality heuristic, severity, gate, threshold, or generated JSON changes.

## Reversal

Remove the model id and resume storage-generated identities. Doing so again makes exact lineage
unavailable to ingestion callers and is not recommended.
