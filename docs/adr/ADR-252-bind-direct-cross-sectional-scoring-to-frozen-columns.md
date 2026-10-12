# ADR-252: Bind direct cross-sectional scoring to frozen columns

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-201
- **Extends:** ADR-025, ADR-140, ADR-149

## Context

The managed cross-sectional loop checks exact panel membership and order against
the position's frozen universe. Direct score_forward calls omit that relationship:
a subset or substituted symbol can change both the factor and equal-weight
benchmark while scoring under the original position. The zero-forward shortcut
also accepts mismatched panels without invoking the engine's structural checks.

## Options Considered

1. Require exact ordered columns at direct scorer entry.
   - Pro: reuses the manager's frozen universe identity before any score branch.
   - Con: repeats one cheap identity comparison for managed calls.
2. Trust the manager or require only a matching column count.
   - Pro: less validation at the direct boundary.
   - Con: direct subset/substitution/order drift remains possible.
3. Reorder, subset or fill the panel to fit the position.
   - Pro: could recover some caller mistakes.
   - Con: silently transforms source identity and may invent missing prices.

## Decision

At score_forward entry require list(panel.columns) to equal
list(position.universe_symbols), before index access and every zero/nonzero-forward
branch. Refuse mismatches with ValueError. Preserve the original scorer body,
factor reconstruction, static maps, costs, evidence and benchmark arithmetic.
Do not normalize, reorder, subset or fill panel columns.

Matching direct synthetic panels with absent evidence remain supported. Manager
acquisition and fail-soft behavior are unchanged. Price/calendar validity, optional
evidence relationships and complete position reconstruction remain separate rules;
this decision adds no policy on those surfaces.

## Consequences and reversal

Direct and managed scoring measure the same frozen ranked universe and benchmark.
A mismatched raw panel now refuses even if no forward bars have accrued. Calls
pay one ordered column comparison; no factor, estimator, threshold, durable schema,
broker action, source acquisition or generated record changes. Remove the entry
check to reverse this correction and reopen FINDING-201.
