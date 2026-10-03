# ADR-153: Run paper-broker reconciliation after successful accrual

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Codex autonomous session 21 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-083
- **Extends:** ADR-021, ADR-030, ADR-151, and ADR-152

## Context

The paper broker mirrors the managed book into Alpaca's paper account. Its independent 01:45 UTC
schedule merely assumes the 01:30 accrual finished. Separate concurrency groups and creation-time
checkouts make that assumption false for delayed, queued, or manual runs.

GitHub's `workflow_run` `completed` event starts a downstream workflow after the named upstream
workflow finishes. It fires for every conclusion, so the downstream job must explicitly require
`github.event.workflow_run.conclusion == 'success'`. The event resolves on the default branch and
the broker checkout still names `master` explicitly so manual recovery has the same state rule.

## Decision

- Remove paper-broker's independent schedule.
- Trigger it on completed runs of the workflow named `Paper forward accrual`.
- Run the broker job only when that upstream conclusion is `success`, or when paper-broker itself is
  manually dispatched for recovery.
- Check out `ref: master` when the broker job starts.
- Retain the separate non-cancelling `paper-broker` concurrency group. Repeated upstream completions
  may coalesce pending broker runs safely because reconciliation is idempotent and every surviving
  run reads the latest desired book.

The workflow is not dispatched as part of this decision. No broker credentials, orders, generated
data, sizing rule, or validation threshold change.

## Consequences

- Scheduled paper orders cannot precede the corresponding successful book accrual.
- A failed accrual produces no automatic broker run, preserving the last successfully published
  desired state.
- Manual broker recovery remains available and reads current master.
- The equity curve is now sampled after successful accrual rather than at an independent clock; the
  normal cadence remains once per successful trading-day update.

## Options considered

1. **Increase the schedule gap.** Rejected because no finite gap orders manual runs or guarantees a
   slow upstream completion.
2. **Put broker and accrual in one concurrency group.** Rejected because GitHub's single pending
   member can be replaced, and serialization alone does not establish success-dependent execution.
3. **Move broker steps into paper-forward.** Viable but couples generated-file commits and failure
   recovery. A downstream workflow preserves the existing independently retryable broker boundary.

## Reversal

Restore an independent broker schedule and remove the `workflow_run` trigger. That reopens
FINDING-083 unless another mechanism proves successful accrual completion before order placement.
