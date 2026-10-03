# FINDING-083: The paper broker can trade a stale managed book

- **Severity:** High — paper orders can contradict the latest promote/monitor/exit decisions
- **Status:** Resolved by ADR-153
- **Date:** 2026-10-02
- **Affects:** ADR-021, ADR-030, ADR-151, and `.github/workflows/paper-broker.yml`

## Finding

`paper-broker.yml` is scheduled at 01:45 UTC, fifteen minutes after paper-forward's nominal start,
but it has a separate concurrency group and checks out the broker run's creation-time SHA. A slow,
queued, or manually dispatched accrual can therefore still be running when the broker reads
`paper_portfolio.json`. The broker may retain a position the accrual is closing, omit a newly
promoted position, or size from stale lifecycle evidence before placing Alpaca paper orders.

The fifteen-minute offset is not a dependency. Both jobs have fifteen-minute timeouts, and manual
dispatches are not schedule-ordered. ADR-151 refreshes state only after a paper-forward run receives
its own concurrency group; it creates no ordering with paper-broker.

## Required correction

Trigger the broker workflow from successful completion of `Paper forward accrual`, not from an
independent clock. Retain explicit manual dispatch for recovery. The broker job must resolve current
`master` when it starts and must not run after a failed accrual. Its existing idempotent reconcile,
paper-only endpoint guard, independent non-cancelling broker concurrency, equity-curve ownership,
and no-real-money boundary remain unchanged.

Add a static workflow regression for the causal trigger, success guard, and current-master checkout.
Do not dispatch either workflow or place an order while implementing the correction.
