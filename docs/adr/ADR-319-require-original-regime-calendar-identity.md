# ADR-319: Require original regime calendar identity

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 33, ISO 2026-W42
- **Extends:** ADR-012/176/302/318
- **Resolves:** FINDING-270

## Context

The nonnegative horizon guard closes negative-period future labeling, but
positive positional trailing periods still depend on source order. Identical
nonmonotonic source calendars preserve their order through align, allowing a
later calendar price to label an earlier return. Original duplicate calendars
can also expand during alignment, repeating supplied strategy observations in
reported counts, products and Sharpe. Independent direct-helper witnesses show
both; normal ValidationEngine is mitigated by the backtest engine's calendar
check and same-frame return construction. No production occurrence or false
graduate is established.

## Decision

After ADR-318's original window validation and before alignment, require both
original source indexes to be unique and monotonically increasing. Raise
ValueError if either fails. Check each whole original source rather than only
its aligned intersection: later filtering must not hide contradictory identity.
Reuse the established ADR-176/302 pandas index predicates, without sorting,
deduplication, copying, timezone normalization or source repair.

Preserve the existing window-check precedence, default20, valid zero horizon,
inner alignment, trailing return, warmup-bull labels, grouping, compounding,
Sharpe and return objects. Ordered generic, naive and aware indexes keep their
existing behavior; empty and singleton ordered sources remain valid. Unequal
ordered sources still use the existing intersection, including disjoint-empty
results. Singleton NaT is not an ascending calendar and now refuses.

No specific index type, timezone, cadence, source completeness, exact symbol
provenance or executable switching-account guarantee is added. Pairwise timezone
incompatibilities and other native alignment limitations retain their behavior.
Source value validity and native arithmetic remain separate. No report schema,
threshold, gate/search identity, accounting-v14, generated data or cohort change.

## Options considered

1. Guard both original calendars before alignment.
   Chosen: prevents future calendar order and duplicate identity expansion.
2. Guard only the aligned intersection or strategy-return calendar.
   Rejected: filtering can hide original invalid identity, and duplicate market
   dates alone can repeat valid strategy observations.
3. Sort/deduplicate inputs.
   Rejected: changes observation order or chooses among conflicting rows.
4. Require identical UTC daily calendars.
   Rejected: broader source/cadence policy, losing current generic, naive and
   partial-intersection compatibility without evidence for that change.

## Verification and reversal

Observe failing tests before code for both original calendars: descending,
shuffled, duplicate and NaT identities, invalid rows outside the intersection,
refusal before align, the actual positive-horizon future-label and duplicate
expansion witnesses. Preserve invalid-window precedence, valid generic/naive/
aware, partial, disjoint, empty, singleton and zero-horizon behavior. Hypothesis
checks invalid rotated sources and exactly-once intersection accounting for
ordered unique sources. Twenty-four valid pre-edit payloads are frozen; source
AST must retain the entire prior module after removing only the new calendar
loop and restoring its docstring.

Independent review, foreground full gates and exact CI precede publication.
Removing only the calendar loop reopens FINDING-270; retain the evidence if
reversing this contract.
