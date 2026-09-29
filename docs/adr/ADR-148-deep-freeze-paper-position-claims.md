# ADR-148: Deep-freeze paper-position claims

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Codex autonomous session 3 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-078
- **Extends:** ADR-019, ADR-020, ADR-023, ADR-033, ADR-073, ADR-139, and ADR-147

## Context

ADR-147 hardened the discovery experiment that produces a paper position, but the position and its
latest forward score remain shallowly frozen. Their nested strategy parameters, lifecycle reasons,
equity curve, and quality evidence can mutate in place and serialize as a different out-of-time claim
under the same freeze identity. Construction also permits contradictory lifecycle and score evidence.

All 44 committed positions already satisfy the relationships below. Historical scores may legitimately
have an empty curve (before ADR-023) or absent evidence (before ADR-139), and those states must remain
readable rather than receiving invented history.

## Options Considered

1. **Deep-freeze and validate the complete graph at `PaperPosition`.**
   - Pro: one boundary protects construction, JSON reload, and every store write while preserving
     legacy nullable/empty states.
   - Con: managed updates must reconstruct instead of using Pydantic's validation-bypassing copy.
2. **Make every nested score and evidence model globally deeply immutable.**
   - Pro: protects independent uses too.
   - Con: changes broader behavior without auditing every producer and consumer.
3. **Rely on the JSON store and trusted portfolio manager.**
   - Pro: no model changes.
   - Con: the store serializes whatever mutable state exists, and the manager currently bypasses
     validation on every update.

## Decision

Deep-freeze the complete durable claim graph at `PaperPosition` construction and JSON load using the
shared ADR-145/147 defensive-freeze primitive. Preserve JSON arrays and objects, empty legacy equity
curves, and nullable legacy evidence.

Require open positions to have neither close time nor exit reasons; require closed positions to have
both. A score with evidence must name the position symbol. Forward counts and scalar statistics must
be finite and non-negative where applicable. When a forward-equity curve is present, require exactly
one point per declared bar, strictly increasing timestamps after the freeze boundary, finite positive
equity values, and terminal values equal to the stored strategy and buy-and-hold returns. Managed
score and exit updates must reconstruct through `PaperPosition.model_validate`. The JSON store must
also revalidate each model dump before writing, so an unchecked Pydantic copy cannot bypass the
durable boundary.

## Consequences

- A persisted paper claim cannot drift through caller-owned or public nested mutation.
- Lifecycle state, acquisition evidence, and non-empty forward curves describe one coherent claim.
- Legacy empty curves and absent evidence remain readable without fabricated provenance.
- Exit policy, strategy formulas, paper sizing, and every validation threshold remain unchanged.

## Reversal

Restore shallow containers or unchecked managed copies. That would reopen FINDING-078 and is not
recommended.
