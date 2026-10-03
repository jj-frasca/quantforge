# ADR-156: Harden quality-report claims

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Codex autonomous session 22 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-088
- **Extends:** ADR-006, ADR-135, ADR-136, ADR-145, and ADR-150

## Context

ADR-006 makes `DataQualityReport` the mandatory auditable gate between normalized vendor data and
research. ADR-135/136 give each report durable source and UUID identity. Model-level freezing does
not protect its nested issue/context containers, and repository writers trust model instances even
though Pydantic unchecked copies bypass validation. One report identity can therefore change its
computed verdict or persisted provenance after construction.

## Options Considered

1. **Deep-freeze at the data model and revalidate at both repositories.**
   - Pro: every construction, API, SQL, research-lineage, and in-memory path shares one boundary.
   - Con: requires small JSON-compatible immutable container implementations in the data layer.
2. **Reuse the research-layer claim-freeze helper.**
   - Pro: less code.
   - Con: reverses the dependency direction by making foundational data models depend on research.
3. **Copy only inside repositories.**
   - Pro: protects storage snapshots.
   - Con: callers and API responses still observe mutable reports, while unsupported context values
     fail late and inconsistently at JSON or database serialization.

## Decision

Make `DataQualityIssue` and `DataQualityReport` one complete defensive data-layer boundary.
Recursively copy and freeze context mappings/sequences, accepting only JSON-compatible null,
boolean, string, integer, and finite-float leaves with string mapping keys. Store report issues as
an immutable ordered sequence. Explicit serializers preserve the existing JSON object/array schema.

Both `InMemoryPriceBarRepository.save_quality_report` and
`TimescaleDBPriceBarRepository.save_quality_report` reconstruct incoming model dumps through
`DataQualityReport` before retaining state or opening a database session. The stores add no
business rules; they delegate to the authoritative model exactly as ADR-150 does for experiment
pools.

## Consequences

- A report's UUID, source, issue graph, and computed pass/fail verdict cannot drift after validation.
- JSON/API/JSONB representations retain their existing shapes and ordinary engine contexts remain
  unchanged.
- Unsupported or non-finite context fails before persistence instead of at a serializer or database.
- No check, severity, heuristic wording, gate behavior, threshold, or SQL schema changes.

## Reversal

Restore mutable issue/context containers or trust instantiated reports at repository writes. That
would reopen FINDING-088 and is not recommended.
