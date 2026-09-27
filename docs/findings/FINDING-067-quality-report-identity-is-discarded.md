# FINDING-067: Persisted quality-report identity is discarded

- **Severity:** High
- **Status:** Resolved by ADR-136
- **Found:** 2026-09-26, Codex autonomous session 26
- **Affects:** `DataQualityReport`, ingestion responses, experiment lineage

## Finding

ADR-006 requires each persisted quality report's id to be recorded in `ExperimentManifest`, but
the canonical report has no id. The TimescaleDB repository generates a fresh UUID only while
inserting the row, returns nothing, and discards that UUID. The ingestion result and API therefore
cannot expose the durable row identity, so callers cannot populate `data_quality_report_id` with
the evidence that was actually checked. The manifest field exists, but the ingestion boundary
cannot supply its value.

## Required correction

Give every canonical `DataQualityReport` a stable UUID at creation and persist that exact UUID as
the row primary key. Keep the identity on ingestion/API responses so experiment construction can
record it. Existing direct constructors remain source-compatible through a default factory; do not
invent links for historical rows or manifests.
