# ADR-163: Harden standalone experiment manifest claims

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 27 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-094
- **Extends:** ADR-137, ADR-138, ADR-145, and ADR-147

## Context

The experiment manifests are the durable statement of which code, parameters, data, and validation
configuration produced a research result. Complete experiment boundaries relate them to embedded
evidence, but the single-name manifest itself performs no identity validation and the panel
manifest exposes a mutable component list. Invalid or later-mutated lineage can therefore exist
before attachment or in direct consumers.

All committed manifest records already satisfy the stronger identity contract, so no generated-data
migration is required.

## Decision

Use one shared manifest identity contract across single-name and panel claims:

- creation timestamps must be timezone-aware and normalize to UTC;
- executed revisions must be full 40-character lowercase hexadecimal Git SHAs;
- parameter and present validation-config hashes must be 64-character lowercase hexadecimal SHA-256
  values;
- strategy, adapter, source/benchmark identity, and symbols must be non-empty, with symbols stripped
  and uppercased;
- request start dates must precede end dates.

`ExperimentManifest` will apply those rules directly and continue allowing a null validation hash
and quality-report UUID for historical/direct uses. `PanelComponentManifest` will revalidate model
instances. `CrossSectionalManifest` will require non-empty strategy/benchmark identity, reconstruct
every component, and expose the ordered components through an immutable JSON-array-compatible list.
Existing outer experiment equality and evidence-link checks remain authoritative.

This changes no acquisition behavior, data-quality rule, statistic, selector, gate, threshold,
candidate budget, workflow, or persisted JSON shape.

## Alternatives considered

1. **Rely only on outer experiment validation.** Rejected: manifests are constructed and may be
   consumed before attachment, and lineage identity belongs at the lineage model boundary.
2. **Freeze only the panel list.** Rejected: impossible single-name identity and unchecked component
   instances would remain serializable.
3. **Require quality/config UUIDs on every manifest.** Rejected: the existing model explicitly
   supports historical and direct uses where those links are honestly absent.

## Consequences

- Standalone lineage records cannot describe empty code/input/config identity or impossible ranges.
- Panel evidence cannot be removed or reordered after validation.
- Existing committed records and JSON shapes remain compatible.
- Outer experiment validation continues to bind manifests to the selected trial and quality reports.

## Reversal

Restore permissive scalar acceptance or mutable panel components. That reopens FINDING-094 and is
not recommended.
