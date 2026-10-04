# ADR-164: Harden research dataset evidence identity

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex interactive continuation under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-095
- **Extends:** ADR-137, ADR-139, ADR-140, and ADR-156

## Context

Dataset evidence records the exact acquisition identity supporting discovery and forward decisions.
Normal quality reports already freeze and validate their nested graph, but unchecked evidence
instances bypass that field boundary when attached to direct forward scores. Both evidence and
the direct dataset constructor also accept ambiguous naive acquisition bounds.

## Options Considered

1. **Make evidence the shared complete identity boundary.**
   - Pro: field and nested-report validation apply to direct, nested, and deserialized evidence;
     datasets share the same interval and provenance contract.
   - Con: dataset construction reconstructs the small report snapshot once more.
2. **Validate separately in every forward consumer.**
   - Pro: limits each change to one consumer.
   - Con: duplicates rules and leaves discovery and future direct consumers inconsistent.
3. **Add deep-freeze wrappers only.**
   - Pro: follows earlier claim-immutability work.
   - Con: valid reports are already deeply immutable; wrappers cannot reject unchecked invalid fields.

## Decision

Set `ResearchDatasetEvidence` to revalidate model instances. Require `start` and `end` to identify
timezone-aware instants, normalize both to UTC, and retain the existing ordered interval, passed
report, matching source, non-empty adapter, and full Git revision checks. Direct `ResearchDataset`
construction validates through its evidence projection and retains that validated report and UTC
bounds before applying its existing frame checks. Normal single-name and cross-sectional score
construction therefore revalidates nested evidence without separate consumer rules.

## Consequences

- Unchecked evidence copies cannot bypass nested report identity validation at normal attachment.
- Naive bounds fail with structured errors; aware offsets preserve their instants in canonical UTC.
- Direct dataset and persisted evidence identity share one contract instead of duplicated checks.
- Legacy absent evidence and existing JSON objects/arrays remain unchanged. No generated-data
  migration, acquisition behavior, quality check, financial statistic, gate, threshold, or workflow
  changes. The 12 inspected committed forward-evidence records already have aware bounds.
- Frame ownership and unchecked outer-score copies remain separate audit tasks.

## Reversal

Restore the permissive evidence instance configuration and independent dataset checks. That reopens
FINDING-095 and is not recommended.
