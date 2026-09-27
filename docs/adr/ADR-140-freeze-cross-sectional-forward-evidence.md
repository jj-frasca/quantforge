# ADR-140: Freeze cross-sectional forward universe and evidence

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 29 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-071
- **Extends:** ADR-006, ADR-025, ADR-138, and ADR-139

## Context

A cross-sectional forward position is one claim over a fixed ranked universe. Unlike a single-name
position, omitting one unavailable series changes both the strategy's ranks and its equal-weight
benchmark. The production driver currently narrows the panel on fetch failure, passes unchecked
frames to the book manager, and persists only derived score values.

## Options Considered

1. **Require a complete mapping of quality-checked datasets for the frozen universe.**
   - Pro: preserves the actual factor and benchmark while making the score self-contained.
   - Con: one unavailable component defers the entire factor's update for that cycle.
2. **Continue scoring the available subset and label it.**
   - Pro: maximizes daily score availability.
   - Con: measures a different strategy and benchmark on each failure pattern; results are not
     comparable through time.
3. **Forward-fill a missing symbol.**
   - Pro: preserves the column name.
   - Con: invents prices, distorts ranks, and can create stale artificial positions.

## Decision

The production cross-sectional panel provider returns an exact mapping from every frozen symbol to
a passed `ResearchDataset`. Before scoring, the manager validates exact membership, each report's
symbol, one common executed revision, and exact post-alignment panel columns in frozen order. A
fetch, quality, insufficient-history, calendar, or identity failure leaves the position and its
prior score unchanged for that cycle. No subset score is emitted.

Every new production `CrossSectionalForwardScore` stores the ordered
`ResearchDatasetEvidence` list for all frozen components. Legacy persisted scores and direct
synthetic calls remain readable with absent evidence. The factor parameters, cost, lifecycle
thresholds, benchmark definition, and forward-return math do not change.

## Consequences

- One transient vendor failure can delay monitoring but cannot redefine the frozen factor.
- Each durable score proves the exact checked evidence and code revision for every ranked symbol.
- Forward panel identity now matches the claim shape already required for discovery by ADR-138.

## Reversal

Restore subset scoring and plain panels. This would again make a frozen factor's identity depend on
daily vendor availability and is not recommended.
