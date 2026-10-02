# FINDING-081: Queued paper accrual checks out stale generated state

- **Severity:** High — a serialized accrual can still recompute and conflict with an already-published accrual
- **Status:** Resolved by ADR-151
- **Date:** 2026-10-02
- **Affects:** ADR-030 and `.github/workflows/paper-forward.yml`

## Finding

GitHub Actions concurrency correctly serialized a manually dispatched paper-forward run and the
delayed scheduled run on 2026-10-01, but it did not refresh the queued run's event SHA. The manual
run published `paper_portfolio.json`; four seconds later the queued run started and the default
checkout restored the older SHA captured when it was created. It recomputed the same accrual from
stale generated state, committed a second divergent version, and hit a rebase conflict on the
single-writer file. Its retry loop then retried inside the unresolved rebase and could not recover.

ADR-030 removes independent writers, but serialization alone does not make a queued workflow's
default event checkout current. The observed failed run is GitHub Actions run `36830814222`; the
serialized successful predecessor is run `36830792906`.

## Required correction

The paper-forward job must resolve and check out the current `master` ref when the job actually
starts, after any concurrency wait, rather than the run's creation-time SHA. Preserve the existing
non-cancelling concurrency group, generated-file ownership, schedule, calculation, and thresholds.
Add a static workflow regression so removing the explicit current-master checkout fails locally.
