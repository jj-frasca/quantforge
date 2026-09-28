# ADR-143: Make fundamental score snapshots immutable and finite

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 31 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-074
- **Extends:** ADR-138, ADR-140, and ADR-142

## Context

ADR-142 preserves the mappings that define value and quality factor trials, but Pydantic's frozen
model setting is shallow: its nested dictionaries remain mutable. The fields also accept non-finite
floats that do not round-trip through JSON and direct construction can bypass the producer's
panel-order projection. A persisted research input is not frozen if its values can change without a
new experiment identity.

## Options Considered

1. **Validate and wrap the existing JSON-object mapping in an immutable dictionary subtype.**
   - Pro: preserves the durable JSON schema, mapping interface, and deliberate missing-key semantics.
   - Con: requires one small shared snapshot type and explicit mutation guards.
2. **Store tuples of score entries.**
   - Pro: native deep immutability.
   - Con: changes the new durable JSON shape and every registry caller for no methodological gain.
3. **Trust producer-side projection and document that frozen models are shallow.**
   - Pro: no code change.
   - Con: deserialization and in-process callers remain able to change or corrupt factor identity.

## Decision

Use one shared immutable score-map boundary for `CrossSectionalExperiment` and
`CrossSectionalPosition`. On every construction and JSON load it must:

- defensively copy the supplied mapping;
- reject `NaN` and positive or negative infinity;
- require every key to belong to the frozen universe and follow that universe's order;
- preserve absent keys as deliberate missingness and preserve `None` as legacy/unsupplied state;
- serialize as the existing JSON object and round-trip with identical key order and values; and
- reject all ordinary in-place dictionary mutation operations.

Search projection remains the canonical producer, while the model boundary independently enforces
the same contract for persisted or hostile input. No factor formula, selection rule, gate,
benchmark, lifecycle threshold, or generated record changes.

## Consequences

- An experiment or position's fundamental factor inputs cannot drift after model construction.
- Invalid persisted values fail closed instead of becoming JSON null or changing rank missingness.
- Existing ADR-142 records retain their additive object-shaped fields and legacy null semantics.

## Reversal

Return to mutable dictionaries and producer-only validation. This would make durable experiment
identity advisory and is not recommended.
