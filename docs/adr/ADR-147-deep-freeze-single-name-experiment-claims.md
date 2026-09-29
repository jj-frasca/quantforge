# ADR-147: Deep-freeze single-name experiment claims

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Codex autonomous session 2 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-077
- **Extends:** ADR-014, ADR-016, ADR-017, ADR-023, ADR-029, ADR-079, ADR-137, and ADR-145

## Context

ADR-145 established a defensive claim-graph boundary for cross-sectional experiments, while the
older and much larger single-name `Experiment` pool remains shallowly frozen. Its searched names,
trials, selected graduate, gate verdict, fundamental screens, valuation flags, manifest, and quality
report contain mutable lists or dictionaries. Those objects can change after their relationships
have been validated and then serialize as a different claim under the same identity.

A read-only compatibility audit of all 3,281 committed `data/research_pool` records found that every
row already satisfies the proposed relationships. This includes 242 legacy records with no
`selected_trial_index`; they continue to resolve through ADR-079's historical max-DSR fallback.

## Options Considered

1. **Deep-freeze and validate the complete graph at the `Experiment` boundary.**
   - Pro: gives construction and deserialization one durable invariant while preserving legacy JSON.
   - Con: requires explicit immutable-container materialization and relationship checks.
2. **Make every shared nested model deeply immutable globally.**
   - Pro: removes mutable containers wherever those models appear.
   - Con: changes broad application behavior without auditing every independent producer and consumer.
3. **Rely on stores and trusted producers.**
   - Pro: no model changes.
   - Con: in-memory use and later serialization still observe drift, and hostile JSON can combine
     individually valid records into an internally false claim.

## Decision

Deep-freeze the complete single-name experiment claim graph at `Experiment` construction and JSON
load. Reuse a research-wide defensive-freeze primitive, while leaving shared nested model classes
unchanged. Preserve JSON arrays and objects and ADR-079's nullable selected-index compatibility.

When trials exist, their ordered names must match `strategy_names`; a persisted best strategy and
selected index must resolve to the same trial. Any graduate must match that trial's strategy and
parameters, equal the best gate result, carry a passing verdict, and agree with structured holdout
identity when present. Manifest strategy, parameter hash, and validation configuration must bind to
the same selected trial and experiment. Symbol-bearing fundamental and valuation evidence must bind
to the experiment symbol, and failed fundamentals or distress evidence cannot coexist with a
graduate. Existing quality-lineage requirements remain mandatory. Production valuation enrichment
must reconstruct through `Experiment.model_validate` instead of unchecked `model_copy(update=...)`.

## Consequences

- A stored single-name experiment cannot drift through caller-owned or public nested mutation.
- Construction and JSON reload enforce one coherent selected-trial, graduate, manifest, and evidence claim.
- Existing committed pool records and legacy nullable selected indices retain their external schema.
- Shared `Trial`, `Graduate`, `GateResult`, fundamentals, and quality-report models retain their
  independent behavior outside an experiment boundary.

## Reversal

Restore shallow nested collections or move these invariants into individual producers and stores.
That would again allow a validated record to drift or accept inconsistent JSON and is not recommended.
