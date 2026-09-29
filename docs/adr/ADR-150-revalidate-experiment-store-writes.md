# ADR-150: Revalidate experiment store writes

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Codex autonomous session 3 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-080
- **Extends:** ADR-016, ADR-024, ADR-145, and ADR-147

## Context

The experiment models now validate and deeply freeze complete scientific claims, but their JSON
stores trust already-instantiated models. An unchecked Pydantic copy can therefore bypass model
validation at the final durable write and leave a pool that fails on its next read.

## Options Considered

1. **Revalidate each incoming model dump before any write.**
   - Pro: preserves one authoritative model boundary and fails before touching the current file.
   - Con: adds one reconstruction per incoming row.
2. **Duplicate selected-trial and lineage checks in each store.**
   - Pro: can check only selected relationships.
   - Con: creates three drifting partial validators and does not guarantee deep graph reconstruction.
3. **Treat model instances as trusted.**
   - Pro: no store change.
   - Con: `model_copy` is a documented validation bypass; trust is not enforced by the type.

## Decision

The monolithic single-name, partitioned single-name, and cross-sectional JSON writers reconstruct
all incoming experiments through their concrete model boundary before creating directories or
writing bytes. Existing rows loaded from disk are already validated. Retention and deduplication run
on the validated incoming records with their existing semantics.

The stores do not add their own business rules. They delegate to ADR-145/147's model validators so
construction, reload, and durable write share one claim definition.

## Consequences

- Validation-bypassing copies cannot corrupt a research pool.
- Rejected writes leave existing files unchanged.
- Pool schemas, retention, trial denominators, and generated data remain unchanged.

## Reversal

Serialize incoming model instances directly. That would reopen FINDING-080 and is not recommended.
