# ADR-145: Deep-freeze cross-sectional experiment claims

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Codex autonomous session 2 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-076
- **Extends:** ADR-024, ADR-138, ADR-142, ADR-143, and ADR-144

## Context

ADR-143 made fundamental snapshots immutable and ADR-144 froze forward-position reconstruction
identity, but the originating `CrossSectionalExperiment` remains a shallowly frozen graph. Its
ordered universe, searched strategy names, finalist trials, selected graduate, gate verdict,
quality reports, and panel manifest contain mutable lists or dictionaries. Those objects can change
after their cross-field relationships have been validated and then serialize as a different claim
under the same experiment identity.

## Options Considered

1. **Deep-freeze the complete graph at the experiment boundary.**
   - Pro: gives the durable record one defensive construction and deserialization boundary without
     changing unrelated single-name model behavior.
   - Con: requires explicit immutable container materialization and JSON serializers for the
     experiment's nested compatibility models.
2. **Make every shared nested Pydantic model deeply immutable globally.**
   - Pro: improves both single-name and cross-sectional records at once.
   - Con: broadens this correction across many producers and persisted schemas without first
     auditing their mutation and compatibility assumptions.
3. **Rely on stores to serialize immediately after construction.**
   - Pro: no model changes.
   - Con: in-memory stores, forward promotion, reports, and later writes still observe mutable
     state; construction-time lineage validation remains bypassable after the fact.

## Decision

Deep-freeze the complete cross-sectional experiment claim graph at
`CrossSectionalExperiment` construction and JSON load. Defensively reconstruct nested records,
materialize ordered collections as immutable sequences, and wrap parameter/context mappings in
immutable defensive copies. Preserve existing JSON object and array shapes through explicit
serialization. The boundary must also validate that the selected trial, best gate result, graduate,
manifest, reports, and universe describe one internally consistent claim. Shared single-name model
classes remain unchanged until separately audited.

## Consequences

- A stored cross-sectional experiment cannot change through either caller-owned input mutation or
  its public nested collections.
- Construction and JSON reload enforce the same complete claim relationships rather than trusting
  a producer that happened to build the row correctly.
- Existing JSON records and nullable legacy lineage remain readable with the same external schema.
- This adds cross-sectional boundary code instead of globally changing shared `Trial`, `Graduate`,
  `GateResult`, or quality-report semantics; those broader surfaces remain separate audit targets.

## Reversal

Restore shallow nested collections or move the invariant into stores. That would again allow a
validated experiment to drift before later use or serialization and is not recommended.
