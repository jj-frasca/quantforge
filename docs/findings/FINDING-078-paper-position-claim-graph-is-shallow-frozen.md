# FINDING-078: Paper-position claim graph is shallow-frozen

- **Severity:** High — a durable forward claim can change under the same frozen strategy identity
- **Status:** Resolved by ADR-148
- **Date:** 2026-09-29
- **Affects:** ADR-019, ADR-020, ADR-023, ADR-033, ADR-073, and ADR-139 paper records

## Finding

`PaperPosition` and `ForwardScore` declare `frozen=True`, but their parameter dictionaries, exit
reasons, forward-equity lists, and nested quality-report issue/context collections remain mutable.
Caller-owned or public in-place edits therefore change the next JSON serialization without changing
the position's symbol, strategy, freeze time, or score timestamp.

The durable boundary also accepts contradictory lifecycle and evidence claims: an open position may
carry a close time and exit reasons, a closed position may omit either, and a score's quality report
may name a different symbol. Non-empty forward curves are not required to match their declared bar
count, ordered post-freeze timestamps, or terminal strategy/buy-and-hold returns. Production currently
uses unchecked `model_copy(update=...)` when adding scores and close verdicts, so later boundary
validation cannot protect those updates.

A read-only audit found all 44 committed `data/paper_portfolio.json` positions already satisfy the
proposed lifecycle, evidence-symbol, forward-curve length, timestamp, and terminal-value
relationships. Legacy scores with an empty curve or absent evidence remain intentionally supported.

## Required correction

Deep-freeze the complete durable paper-position graph at construction and JSON load while preserving
the existing JSON object/array schema. Revalidate lifecycle state, score evidence symbol, finite
forward statistics, non-negative count geometry, and any non-empty curve's count/order/post-freeze/
terminal-value relationships. Preserve legacy empty curves and nullable evidence. Production managed
updates must reconstruct through `PaperPosition.model_validate` instead of unchecked model copies,
and the JSON store must revalidate claims before writing. Do not change exit thresholds, strategy
behavior, paper sizing, generated data, or historical scores.
