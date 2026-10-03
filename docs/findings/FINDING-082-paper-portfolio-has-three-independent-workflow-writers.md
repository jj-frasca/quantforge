# FINDING-082: The paper portfolio has three independent workflow writers

- **Severity:** High — independent generated snapshots can conflict or overwrite lifecycle state
- **Status:** Resolved by ADR-152
- **Date:** 2026-10-02
- **Affects:** ADR-030, ADR-151, `paper-forward.yml`, `daily-discovery.yml`, and `hunt.yml`

## Finding

`paper-forward.yml`, `daily-discovery.yml`, and `hunt.yml` all read, regenerate, commit, and push
`data/paper_portfolio.json`, but they use three unrelated concurrency groups. The discovery and
hunt runs can last hours and check out the repository before their searches begin. A paper accrual
can therefore publish lifecycle or score changes while either search is still running; the later
search then commits a portfolio derived from the stale checkout. The retry loops rebase commits,
but generated JSON has no safe semantic merge, so a textual conflict stops publication and a
non-conflicting replacement can still embody stale lifecycle state.

ADR-151 fixes queued runs only inside `paper-forward`'s own concurrency group. It explicitly leaves
cross-workflow writers for separate review, and cannot serialize the other two groups.

A single shared GitHub concurrency group is not lossless. GitHub permits at most one running and one
pending member of a group; a newly queued workflow can replace an older pending workflow even when
`cancel-in-progress` is false. Sharing one group would trade generated-state conflicts for silently
dropped discovery, hunt, or accrual work.

## Required correction

Make paper-forward the only production workflow that mutates `paper_portfolio.json`. Discovery and
hunt publish research-pool evidence only. This does not lose promotions: `scripts/paper.py` already
loads the complete committed pool and idempotently offers every graduate to `manage_portfolio`, so
the next paper-forward run picks up any graduate published by either search. Retain ADR-151's
current-master checkout and non-cancelling paper-forward serialization.

Add a static workflow/script contract proving no discovery or hunt production path names or stages
the paper portfolio. Do not edit the generated file during the correction.
