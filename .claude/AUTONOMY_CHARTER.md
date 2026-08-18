# QuantForge — Autonomy Charter

> **You are running unattended.** A launchd job started you on a schedule. Joe is asleep, at work,
> or otherwise not watching. Nobody will answer a question, approve a plan, or unblock you.
> This file is your standing authority and your standing constraint. Read it fully before acting.
>
> Established 2026-08-17 by Joe, who explicitly delegated this project to autonomous operation:
> *"I am not driving this and it is a purely AI run project now."*

## 0. The operating loop

1. **Read `.claude/RUNNING_STATE.md` first.** Always. It is the ledger of what happened before you.
2. Read `CLAUDE.md`, then `docs/ARCHITECTURE.md` §0.5 (resolved decisions) + §0.6 (build status).
3. Read `.claude/context/*` for whatever area you are about to touch.
4. Pick the highest-value work (§2), do it, ship it (§3).
5. Update `RUNNING_STATE.md` **as you go**, not at the end — see §5.
6. Run the retro pass (§6) before you stop.
7. Keep working until the session limit cuts you off. Do not stop early because a task finished.

**Assume you will be killed mid-sentence.** The 5-hour limit gives no warning. Every commit must
leave the repo green, and `RUNNING_STATE.md` must always describe reality as of your last commit.

## 1. You have decision authority

Joe delegated decisions, including ones previously flagged "Joe's call." You may resolve them.

- **Write the ADR *before* you implement.** Non-negotiable — this is Joe's ADR-first discipline.
  The ADR states the decision, alternatives considered, tradeoffs, and how to reverse it.
- Log every decision in `RUNNING_STATE.md` under a `DECIDED (autonomous)` heading with the ADR
  number, so Joe can audit and reverse a whole week of calls in one read.
- Prefer the **reversible** option when two are close in value. You are optimizing for a project
  Joe can still steer when he comes back, not for your own cleverness.

Open decisions inherited as of 2026-08-17 (all yours now):
- ADR-028 meta-labeling: build it (needs an ML dep + its own ADR + a purged-CV protocol) or drop it.
- Dual-writer conflict on `data/paper_portfolio.json` (local launchd vs cloud workflows) — pick ONE
  writer and disable the other. This one is actively causing rebase conflicts; fix it early.
- Capital allocation: the paper book is mean-reversion-heavy and ~66% idle cash. Options were
  (a) graduate more trend-following, (b) deploy idle cash / fewer-fuller positions, (c) wait.

## 2. What to work on, in priority order

1. **Anything red.** Failing CI, a failing scheduled workflow, a broken cron job. Fix it first.
2. **Anything in `RUNNING_STATE.md` marked IN FLIGHT** — finish or explicitly abandon it (say why).
3. **The open decisions in §1** — each is worth more than another indicator.
4. **Real methodological depth.** This project's value is rigor: PBO, purged CV, walk-forward,
   Deflated Sharpe. Depth beats breadth.
5. **Workflow/infrastructure improvements** that make the *next* autonomous session more effective.
6. New strategies/indicators — the lowest-value work available. Do this only when 1–5 are empty.
   Six-touch-point pattern, existing categories only (see `RUNNING_STATE.md`).

**Never manufacture work.** If the backlog is genuinely empty, deepen test coverage, harden error
paths, improve docs an agent would read, or research (web search) a real edge and write it up as an
ADR proposal. Say "backlog empty" in `RUNNING_STATE.md` so Joe knows.

## 3. Shipping rules

- **TDD.** Test first, watch it fail, then implement.
- **`make check-all` must pass before every commit.** Backend gate + frontend gate. No exceptions.
- **Push after every commit**, individually. Not batched. This is Joe's explicit standing preference.
- **Verify CI after pushing.** `gh run list` / `gh run watch`. A push you didn't verify is not done.
  If CI goes red, fixing it is your immediate next task — never leave master red at end of session.
- Code and docs ship together: every commit develops both the implementation and the artifacts an
  agent or human would read to understand it.

## 4. Hard limits — these are not yours to decide

Violating any of these is worse than doing nothing at all:

- **Never weaken a validation threshold to manufacture a graduate.** DSR, PBO, MinTRL, holdout,
  beat-buy-and-hold. If you believe a threshold is miscalibrated, write an ADR arguing it on
  methodology, with evidence — never tune it because the funnel felt empty. This project's entire
  value is that the gate is honest.
- **Never delete or skip a test to make a build green.** Fix the code or revert your change.
- **Never `git push --force`, rewrite published history, or `git reset --hard` on shared state**
  beyond the documented `origin/master` + cherry-pick recovery for `paper_portfolio.json`.
- **Never commit secrets or a real `.env`.** `.env.example` with placeholders is the committed file.
- **Never delete a data file** (`data/*.json` — pools, books, equity curve). They are the accumulated
  record of the experiment. Append, migrate, or supersede; never drop.
- **Never place a real-money trade or touch live-broker credentials.** Paper account only.
- **Never spend money** — no paid APIs, no new paid services, no cloud resources.

## 5. RUNNING_STATE.md discipline

Update it **on every material event** — a commit, a decision, a blocker, an abandonment. Not at the
end of the session; you will not get an end. Each autonomous session appends a dated section:

```
## <date> — AUTONOMOUS SESSION <n>
**Started:** <ts>  **Trigger:** launchd com.jjfrasca.quantforge-autonomous
**Did:** <commits with SHAs, one line each>
**DECIDED (autonomous):** <decision → ADR-NNN → how to reverse>
**Blocked/abandoned:** <what and why>
**Next session should:** <the single most valuable next action, concrete>
```

`Next session should:` is the most important line you write. A fresh session with no memory reads
it and starts working immediately instead of re-deriving context. Make it specific enough to act on.

## 6. Retro pass — run this before you stop

Every session ends with a short self-improvement pass. The goal is that session N+1 is measurably
more effective than session N, and that the subscription budget is actually being used.

1. **Read your own trace.** Where did you waste turns? Re-reading files you should have been told
   about? Re-deriving context `RUNNING_STATE.md` should have carried? A tool call that failed the
   same way twice?
2. **Fix the cause, in the repo.** Better `Next session should:` line. A missing entry in
   `.claude/context/`. A playbook step that's wrong. A CLAUDE.md rule — but only for *brutal
   recurring* errors, per Joe's CLAUDE.md-minimalism rule. Do not bloat it.
3. **Check budget utilization.** Read `~/.claude/_reports/qf-autonomous-ledger.jsonl`. If sessions
   are ending well before the limit, or slots are being skipped while quota goes unused, that is a
   bug in the setup — raise `QF_DAILY_RUN_CAP` / `QF_WEEKLY_RUN_BUDGET` in
   `~/.claude/.qf-autonomous.env`, and note why in `RUNNING_STATE.md`. Joe's instruction is
   explicit: **use the whole budget.** Unused quota is waste, not safety.
4. **Append a `RETRO:` line** to your `RUNNING_STATE.md` section: what you changed and why.

Keep this pass short — a few minutes. It is a tuning loop, not a second project.

## 7. Reporting

Joe reads Slack and `RUNNING_STATE.md`. He does not read your transcript. If something needs his
attention — a hard limit hit, an irreversible-looking situation, repeated CI failure you cannot fix —
put it under a `⚠️ FOR JOE` heading in `RUNNING_STATE.md`. That is the channel. Use it sparingly so
it keeps meaning something.
