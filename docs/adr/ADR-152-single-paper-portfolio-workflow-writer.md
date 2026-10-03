# ADR-152: Use one workflow writer for the paper portfolio

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Codex autonomous session 21 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-082
- **Extends:** ADR-030 and ADR-151

## Context

Three workflows mutate `data/paper_portfolio.json` under unrelated concurrency groups. Their
rebase retries cannot merge independently regenerated book snapshots. ADR-151 refreshes a queued
paper-forward checkout, but it does not protect that workflow from daily-discovery or scheduled-
hunt running concurrently from older repository state.

GitHub concurrency is not a lossless cross-workflow queue: one group retains only one running and
one pending run, so later arrivals may replace older pending work. A shared group could discard a
discovery, weekly hunt, or daily accrual.

The existing paper-forward calculation already supplies the safe funnel. `scripts/paper.py` reads
the complete committed research pool, promotes every eligible graduate not previously held, and
updates every open position. Promotion is idempotent, and a closed position is never re-added.

## Decision

`paper-forward.yml` is the sole production workflow writer of `data/paper_portfolio.json`.

- Daily discovery consolidates and commits only `data/research_pool`.
- Scheduled hunt searches and commits only `data/research_pool`.
- The local hunt fallback also commits only `data/research_pool`.
- Paper-forward retains ADR-151's explicit current-`master` checkout and its non-cancelling
  `paper-forward` concurrency group.
- The next paper-forward run promotes any graduate that discovery or hunt added to the committed
  pool. No extra workflow dispatch is required.

A repository test scans the production workflow/script contracts so a second paper-portfolio
writer fails locally and in CI.

## Consequences

- Independently scheduled searches cannot overwrite or conflict with paper lifecycle/accrual state.
- Search publication no longer performs recent-price fetches solely for promotion, reducing its
  failure surface and runtime.
- A newly discovered graduate waits until the next scheduled paper-forward run before entering the
  book. This is at most the normal daily forward-testing cadence and preserves its frozen discovery
  evidence.
- Research-pool write collisions between discovery and hunt are not solved here; they are a
  separate generated-state review because their partition merge semantics differ from one-file
  portfolio replacement.

## Options considered

1. **Give all three workflows one concurrency group.** Rejected because an additional arrival can
   replace the group's existing pending run, losing work.
2. **Refresh master immediately before each search publishes, then rerun promotion.** Rejected
   because promotion and lifecycle scoring would still be based on a different snapshot than the
   refreshed file; recomputing after every lost race repeats live network work and remains fragile.
3. **Merge generated JSON after rebase.** Rejected because lifecycle transitions and forward curves
   require domain-aware recomputation, not textual or field-wise merge.

## Reversal

Restore promotion to discovery/hunt and add their portfolio path to workflow staging. Reversal
reopens FINDING-082 unless the replacement provides a durable, lossless queue rather than ordinary
GitHub concurrency.
