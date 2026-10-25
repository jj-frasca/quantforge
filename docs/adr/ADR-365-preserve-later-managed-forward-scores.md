# ADR-365: Preserve later managed forward scores

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session30, ISO2026-W43
- **Resolves:** FINDING-305
- **Extends:** ADR-019, ADR-020, ADR-025, ADR-139, ADR-140, ADR-148, ADR-149

## Context

A newly fetched quality-passing dataset can end before observations already
recorded on an open position. Both managers currently replace the later score
and evaluate lifecycle on that older sample. A real quality-pipeline synthetic
witness replaces four accrued forward observations with an earlier zero-bar
score in both books. This establishes a retention gap, without demonstrating
an actual vendor incident or corrupted generated record.

## Options considered

1. Preserve the complete position when a valid candidate score ends earlier.
   This prevents cutoff rollback and treats unavailable later data like a deferred
   refresh. It requires only a comparison against existing validated score metadata.
2. Accept every quality-passing refresh. Quality and half-open request membership
   do not guarantee response completeness or observation freshness.
3. Merge the old and new curves. Revised prices or different common calendars can
   make the two reconstructions incompatible; merging would invent a new claim.
4. Require fresh data relative to `now` or monotonic bar counts. Neither contract
   is needed to preserve an already observed later cutoff and both broaden scope.

## Decision

In `manage_portfolio` and `manage_cross_sectional_book`, immediately after the
existing candidate score computation and before lifecycle evaluation, compare
`score.as_of` with `position.score.as_of` when a prior score exists. If the
candidate cutoff is strictly earlier, append the original position unchanged
and continue. Do not publish the candidate or evaluate lifecycle on it.

Keep the original score, evidence, curve, lifecycle metadata and identity together.
First scores, equal-cutoff corrections, later cutoffs and terminal positions retain
their existing paths. Do not introduce a helper, field, status, curve merge,
data repair, count threshold, time-of-day freshness rule or source-clock inference.
Pure scoring remains able to evaluate an explicitly supplied historical dataset.
Existing acquisition failures and exception handling remain unchanged.

## Consequences and reversal

A stale response cannot erase a later managed observation cutoff or change
lifecycle from its earlier sample. Monitoring defers until sufficient later source
data returns; this does not guarantee freshness, validate old data, undo an earlier
action, or reconcile broker execution. An intentional correction that removes
later observations requires an explicit correction procedure. Equal-cutoff
updates may still revise history or change bar counts; this is deliberately not
an append-only curve or monotonic-count policy.

No financial formula, lifecycle default, policy hash, validation threshold, schema,
accounting-v14, generated record, frozen cohort or broker action changes. Remove
the two manager cutoff guards to reverse this retention rule and reopen F305.
