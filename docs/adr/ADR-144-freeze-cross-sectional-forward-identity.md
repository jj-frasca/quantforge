# ADR-144: Deep-freeze cross-sectional forward reconstruction identity

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 31 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-075
- **Extends:** ADR-025 and ADR-143

## Context

Cross-sectional positions promise to lock the strategy, searched parameters, quantile, ordered
universe, cost rate, and static fundamental inputs at promotion. ADR-143 made the fundamental maps
deeply immutable, but the parameter dictionary and universe list can still mutate inside the frozen
model. Both are direct inputs to factor reconstruction and evidence validation.

## Decision

At the `CrossSectionalPosition` model boundary:

- defensively copy parameters into an immutable mapping;
- materialize the ordered universe as an immutable tuple;
- serialize those values using the existing JSON object and array shapes; and
- preserve all current values and ordering without adding a new strategy or portfolio threshold.

The experiment model is not included in this correction. Promotion creates a position through this
independent boundary, so forward identity becomes durable even when a legacy or in-process
experiment remains shallow. A complete experiment deep-freeze requires a separate audit because
its trials, graduate, reports, manifests, and selection metadata form one larger claim graph.

## Consequences

Forward scoring, lifecycle evaluation, and panel evidence checks cannot be redirected by in-place
parameter or universe mutation. Existing stored JSON remains readable and new JSON retains the same
schema.

## Reversal

Restore mutable dictionaries/lists on positions. This would again make the freeze boundary
advisory and is not recommended.
