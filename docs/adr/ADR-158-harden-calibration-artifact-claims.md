# ADR-158: Harden calibration artifact claims

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Codex autonomous session 24 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-090
- **Extends:** ADR-037, ADR-053, ADR-080, ADR-102, ADR-103, and ADR-150

## Context

Null and power calibration files are durable methodology evidence. Their Pydantic wrappers are
frozen only at the attribute level: nested arrays, mappings, verdicts, and sweep cells remain
mutable after relationship validation, while unchecked model copies bypass validation entirely.
Workflow writers serialize those objects directly and analysis functions trust model instances.

## Decision

At construction, defensively reconstruct and recursively freeze every nested calibration value,
including graduates, diagnostics, verdicts, scalar projections, errors, attribution maps, and sweep
cells. Preserve the existing JSON array/object schema and legacy empty-field semantics.

Consolidation and methodology inference reconstruct their complete inputs through the authoritative
models before reading or writing evidence. Invalid unchecked copies therefore fail before output or
statistical interpretation. No statistic, sample, seed, search/gate identity, threshold, workflow,
or generated data changes.

## Alternatives considered

1. **Freeze only top-level lists.** Rejected: nested verdicts and category maps could still drift.
2. **Revalidate only at file writes.** Rejected: in-process reports and inference could still read
   a validation-bypassing copy.
3. **Rely on JSON reload.** Rejected: ordinary workflow writers serialize before any reload.

## Consequences

- One validated Type-I or power claim cannot change under the same artifact identity.
- Existing JSON remains backward compatible and generated files are not rewritten locally.
- Hostile in-process copies fail closed at consolidation and inference boundaries.

## Reversal

Restore mutable nested containers or trust instantiated artifacts. That reopens FINDING-090.
