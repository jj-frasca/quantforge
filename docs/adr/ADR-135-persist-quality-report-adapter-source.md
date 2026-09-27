# ADR-135: Persist adapter source on data-quality reports

- **Status:** Accepted
- **Date:** 2026-09-26
- **Deciders:** Codex autonomous session 26 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-066
- **Extends:** ADR-006 and ADR-118

## Context

The quality engine validates source identity but discards it from `DataQualityReport` and
`data_quality_reports`. Durable evidence can prove that a source check passed without saying which
source was checked. Existing rows predate this decision and cannot be reconstructed honestly.

## Options Considered

1. **Add a nullable canonical source field to the report and SQL row.**
   - Pro: makes new evidence self-identifying while representing legacy uncertainty honestly.
   - Con: requires a schema migration and one additional API field.
2. **Recover source later by joining price bars.**
   - Con: reports do not persist their exact range or bar identities; later cache contents may have
     changed or contain multiple vendors, so the join cannot prove historical acquisition identity.
3. **Encode source only inside issue context.**
   - Con: passing reports often have no source-related issue and context is not a stable schema.

## Decision

Add `source: Source | None = None` to `DataQualityReport` and a nullable `source` column to
`data_quality_reports`. `DataQualityEngine.check` records `expected_source` when supplied; otherwise
it derives the source only from a non-empty homogeneous bar set. Mixed source evidence without an
expected adapter remains `None`. `TimescaleDBPriceBarRepository.save_quality_report` persists the
field. Existing rows migrate to `NULL`; no historical source is inferred.

## Consequences

- New pipeline reports durably identify the adapter they checked, including failed mismatches.
- Legacy/direct reports remain readable and explicitly unmeasured for source provenance.
- API responses gain one backward-compatible nullable field.
- No quality heuristic, severity, gate, threshold, or stored generated JSON changes.

## Reversal

Drop the nullable field and column. That would again make durable quality evidence unable to name
its acquisition source and is not recommended.
