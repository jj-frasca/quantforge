# FINDING-088: Quality-report claims are mutable and stores trust copies

- **Severity:** High — persisted gate evidence can change verdict or provenance under one report UUID
- **Status:** Resolved by ADR-156
- **Date:** 2026-10-03
- **Affects:** ADR-006, ADR-135, and ADR-136 quality evidence

## Finding

`DataQualityReport` and `DataQualityIssue` declare `frozen=True`, but the report's issue list and
each issue's context dictionary/list graph remain mutable. Caller-owned context mutation leaks into
an already-created report; public mutation can add or remove an error and therefore flip the
computed `passed` verdict under the same canonical UUID. The in-memory repository retains the same
mutable object, so post-save mutation changes durable test/dev evidence retroactively.

Issue context also accepts arbitrary Python objects and nested non-finite floats even though the
field is stored as JSONB and embedded in JSON research claims. Finally, both memory and TimescaleDB
writers trust instantiated models, so `model_copy(update=...)` can bypass symbol, timestamp, issue,
and verdict validation at the persistence boundary.

## Required correction

Make the complete report graph defensive and JSON-safe at construction/reload: freeze issue order
and recursively freeze context dictionaries/lists while preserving JSON object/array shapes; reject
non-string dictionary keys, unsupported objects, and non-finite floats. Both repository writers
must reconstruct the complete report before retaining it or opening a database transaction, and
invalid input must leave existing state unchanged. Preserve report UUID/source semantics, issue
wording, all quality checks and severities, `passed` computation, SQL schema, and every threshold.
