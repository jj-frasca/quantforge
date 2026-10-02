# ADR-151: Refresh queued paper-forward state at job start

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Codex autonomous session 20 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-081
- **Extends:** ADR-030

## Context

Workflow-level concurrency serializes paper-forward runs, but GitHub binds each run to the SHA at
creation time. A queued run can therefore start after its predecessor publishes while the default
checkout still restores the predecessor's old base. On 2026-10-01 that exact sequence produced a
second paper accrual and a generated-file rebase conflict even though no two jobs ran concurrently.

## Options Considered

1. **Explicitly check out `master` when the accrual job starts.**
   - Pro: resolves the repository state after the concurrency wait and before any calculation.
   - Con: the executed SHA may be newer than the run's creation-time `head_sha`.
2. **Rely on the existing rebase retry after calculation.**
   - Pro: no workflow change.
   - Con: generated JSON has no safe semantic merge, and a conflicted rebase poisons later retries.
3. **Cancel queued or in-progress accruals.**
   - Pro: prevents duplicate work.
   - Con: can discard the only accrual for a trading day and violates the existing non-cancellation
     policy.

## Decision

The paper-forward accrual checkout explicitly uses `ref: master`. The non-cancelling
`paper-forward` concurrency group remains authoritative, so a queued job resolves current master
only when it receives the group and begins execution. A static test requires both contracts.

## Consequences

- A queued manual/scheduled pair reads the predecessor's published portfolio before accrual.
- The calculation, schedule, generated-file ownership, and push policy are unchanged.
- The run's event `head_sha` is no longer proof of the executed checkout; git history remains the
  durable generated-state audit trail.
- Cross-workflow writers that share `paper_portfolio.json` remain a separate concurrency review.

## Reversal

Remove the explicit checkout ref. That would reopen FINDING-081 and is not recommended.
