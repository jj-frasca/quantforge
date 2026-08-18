# ADR-030: The cloud workflows are the single writer of generated data files

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-019 (forward testing / paper trading), ADR-021 (Alpaca paper execution),
  ADR-023 (forward equity series), ADR-026 (maximum token-free discovery)

## Context
`data/paper_portfolio.json` and `data/equity_curve.json` are *generated* files that live in git —
they are the accumulated record of the forward test, so they must be committed, not regenerated.
Two independent systems were writing and pushing them:

1. **Cloud** — `paper-forward.yml` (01:30 UTC Tue–Sat) advances the book, `paper-broker.yml`
   (01:45 UTC) mirrors it to the Alpaca paper account and snapshots the equity curve. Both commit
   with a `git pull --rebase` + 3-attempt retry loop. `daily-discovery.yml` and `hunt.yml` also
   commit `paper_portfolio.json` as part of promotion.
2. **Local** — the launchd job `com.jjfrasca.quantforge-paper` runs `scripts/cron_paper.sh` daily at
   17:30 local, which runs the same `scripts/paper.py`, commits the same file, and does a bare
   `git push` with **no rebase**.

Two writers of one generated file is a lost-update race by construction. It is not theoretical: the
local job's own log ends in

```
 ! [rejected]        master -> master (non-fast-forward)
push failed (network?)
```

after which a *local-only* commit sits on top of a stale master. Every subsequent session inherits a
diverged branch and has to resolve a conflict on a machine-generated JSON file where no meaningful
merge exists — the recurring failure recorded in `RUNNING_STATE.md` on 2026-07-21 and worked around
with `git reset --hard origin/master` + cherry-pick. It is also the failure mode most likely to break
an unattended session's own pushes, which is why the charter names it as the first decision to take.

## Decision
**The cloud workflows are the sole writer of every generated file under `data/`.** The local launchd
paper job is retired: `com.jjfrasca.quantforge-paper` is unloaded and its plist removed from
`~/Library/LaunchAgents`, and `scripts/cron_paper.sh` + `scripts/com.jjfrasca.quantforge-paper.plist`
are deleted from the repo so nothing re-installs it.

The invariant going forward: **a human or agent session never commits a `data/*.json` file that a
workflow also writes.** If a session needs to advance the book, it dispatches the workflow
(`gh workflow run paper-forward.yml`) rather than running the script and committing the result.

## Options Considered
- **Keep local, disable cloud.** Rejected. The Mac is not always awake (a closed lid sleeps), so the
  forward test would silently skip days — and a skipped day in a forward test is unrecoverable data
  loss. The cloud runs on a public repo with unlimited Actions minutes and has succeeded on every
  scheduled run for the last week+.
- **Keep both, add rebase-retry to the local script.** Rejected. It narrows the race window without
  closing it, and it leaves two systems accruing the *same* positions on *different* data vendors
  (local `scripts/paper.py` falls back to yfinance; the cloud passes Alpaca credentials). Same-day
  double accrual on disagreeing prices would corrupt the P&L record — worse than a push conflict,
  because it is silent.
- **Move the generated files out of git** (a release asset, a branch, a DB). Rejected for now: the
  git history of these files *is* the audit trail, and it is what makes the forward test verifiable
  by an outside reader. Revisit only if file size becomes a problem, as it did for
  `research_pool.json` (solved by pruning, not by leaving git).

## Consequences
- No more rebase conflicts on `paper_portfolio.json`; an unattended session can push freely.
- The forward test now advances on the cloud's Alpaca data only — consistent with the broker fills,
  so sizing and fills continue to use the same price source (verified 2026-08-04).
- Accrual happens at 01:30 UTC Tue–Sat instead of 17:30 local. No behavioral change for a daily-bar
  strategy; it is still one accrual per trading day.
- The local Slack scoreboard is not lost — `paper-forward.yml` posts the same scoreboard to the same
  webhook via the `SLACK_WEBHOOK_URL` secret.
- Losing the local job means losing the ability to accrue while GitHub is down. Accepted: a missed
  day is caught up on the next run, because accrual is driven by bar dates, not by run count.

## Reversal
Re-install the launchd job:

```
cp scripts/com.jjfrasca.quantforge-paper.plist ~/Library/LaunchAgents/   # restore from this commit
launchctl load ~/Library/LaunchAgents/com.jjfrasca.quantforge-paper.plist
```

and disable the cloud schedule in `paper-forward.yml` / `paper-broker.yml`. Both files are recovered
from the commit that enacts this ADR. Never run both again.
