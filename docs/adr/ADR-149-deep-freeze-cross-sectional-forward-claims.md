# ADR-149: Deep-freeze cross-sectional forward claims

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Codex autonomous session 3 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-079
- **Extends:** ADR-025, ADR-140, ADR-143, ADR-144, and ADR-148

## Context

ADR-144 froze the factor reconstruction identity, but the position's lifecycle and latest forward
score remain a shallow graph. Its exit reasons, equity curve, and component evidence can mutate and
serialize as a different out-of-time claim under the same factor identity. Neither construction nor
the store binds that score evidence and curve back to the frozen ordered universe.

There is no committed cross-sectional forward book. ADR-025 permits legacy empty curves and ADR-140
permits evidence-null synthetic/legacy scores; both states remain readable rather than receiving
invented history.

## Options Considered

1. **Deep-freeze and validate the complete graph at `CrossSectionalPosition`.**
   - Pro: one boundary protects construction, managed replacement, JSON reload, and store writes.
   - Con: managed updates and stores must reconstruct rather than trust unchecked copies.
2. **Harden only `CrossSectionalForwardScore`.**
   - Pro: improves the score in isolation.
   - Con: cannot bind ordered evidence to the position universe or enforce lifecycle identity.
3. **Rely on the manager's panel checks.**
   - Pro: no durable-model change.
   - Con: later mutation and unchecked copies can still bypass those ephemeral checks.

## Decision

Make `CrossSectionalPosition` the complete durable boundary. Preserve ADR-144's immutable parameter,
universe, and fundamental snapshot shapes, then defensively reconstruct and recursively freeze the
nested score, curve, component evidence, reports, issues, contexts, and exit reasons.

Require open factors to have neither retirement time nor reasons and retired factors to have both.
Require a finite non-negative cost and a unique non-empty ordered universe. Score bar counts must be
non-negative and all return/Sharpe statistics finite. When evidence exists, its ordered report
symbols must exactly equal the frozen universe and all components must name one executed revision.
When an equity curve exists, require one point per declared bar, strictly increasing timestamps
after the freeze boundary, finite positive equity values, and terminal values equal to stored factor
and benchmark returns. Empty curves and absent evidence remain supported.

Managed score/retirement updates must reconstruct through `CrossSectionalPosition.model_validate`.
The JSON store must revalidate every model dump before writing so an unchecked Pydantic copy cannot
bypass the boundary.

## Consequences

- A frozen factor's durable lifecycle, score, and evidence cannot drift through nested mutation.
- Ordered component evidence proves the same panel identity used to reconstruct the factor.
- Legacy empty curves and evidence-null scores remain readable without fabricated provenance.
- Factor math, benchmark semantics, exit policy, thresholds, and generated data remain unchanged.

## Reversal

Restore shallow score/lifecycle containers or unchecked managed/store writes. That would reopen
FINDING-079 and is not recommended.
