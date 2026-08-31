# FINDING-014: the local gate was never hung — it was sharing eight cores with a second checkout

- **Status**: Confirmed by direct measurement, 2026-08-31
- **Found by**: Autonomous session #17
- **Affects**: local `make test` / `make check` wall time only. **No production code, no gate
  threshold, no published result.** CI has always been correct and green.
- **Supersedes**: the "⚠️ FOR JOE — the local test suite no longer finishes" note from session #16

## What was believed

Session #16 ran `make check` on this machine twice. The first run went 70 minutes without
completing and was killed. The second, without coverage, reached 98% and then sat on one pegged
worker for 38 more minutes. The same suite finishes on CI in 8m36s. #16 recorded it as priority 1
for the next session — *"a gate nobody can run locally is red"* — and hypothesised a single hanging
test, which is why `2b0f3ad` added `pytest-timeout` with `--timeout=300 --timeout-method=thread`.

## What is actually true

There is a **second, independent clone of this repository** on the machine at
`/Users/joefrasca/claude-work/quantforge-codex` (HEAD `c29bde0`), driven by a peer agent session.
It runs the same `make test`. Measured at 14:46Z while this session's own `make test` was running:

```
$ ps aux | grep "[p]ytest"
  .../quantforge/backend/.venv/bin/pytest       ... -n auto ...   started 07:33
  .../quantforge-codex/backend/.venv/bin/pytest ... -n auto ...   started 07:37

$ ps aux | grep -c "[q]uantforge/backend/.venv/bin/python"        20
$ ps aux | grep -c "[q]uantforge-codex/backend/.venv/bin/python"  17
$ sysctl -n hw.physicalcpu hw.logicalcpu                          8 / 16
$ sysctl -n vm.loadavg                                            { 36.88 30.96 17.93 }
```

`pytest -n auto` sizes the pool from **logical** cores, so each checkout asks for 16 workers. Two
concurrent gates therefore schedule ~33 test processes against 8 physical cores, and the one-minute
load average sat at **36.9 — about 4.6x oversubscribed**.

## Why this explains every symptom, and a hanging test does not

| Observation (session #16) | Under "one test hangs" | Under contention |
| --- | --- | --- |
| 8m36s on CI vs 70min locally | a hang is unbounded, not 8x | 4.6x load ⇒ ~5-8x wall time |
| Two runs stalled in *different* places | needs two independent hangs | expected; whichever test is unlucky |
| `/usr/bin/sample` showed ordinary pandas / interpreter frames | a hang parks in a lock or a syscall | starved processes sample as running code |
| 98% reached, then one worker alone for 38min | consistent | xdist's last worker runs alone against a full machine |
| CI green on every SHA **including with `--timeout=300` active** | would need a test >300s that only hangs here | no test exceeds 300s anywhere |

The last row is the decisive one. `2b0f3ad` shipped a 300-second per-test timeout and CI passed
with it, which proves no test in the suite legitimately runs that long. A test that hung would have
been named by that timeout. Nothing was named.

## Consequence

The local gate is not broken; it is **unschedulable while a second checkout is running its own**.
That is a different problem with a different fix, and the fix is not in the test suite.

To be precise about what was and was not observed: this session did not watch a contended `-n auto`
run to completion either — it was killed at 26m36s, still running, because by then it was testing
stale code. What is established is the contention itself (measured above), that CI passes the same
suite under a 300s per-test timeout so nothing in it legitimately hangs, and the timings below.

1. `Makefile` gains `PYTEST_WORKERS ?= auto`, used by the `test` target. The default is unchanged,
   so CI and a solo local run behave exactly as before. A session that finds a peer gate running
   drops its own worker count — `make test PYTEST_WORKERS=4` — and gets a schedulable gate instead
   of a two-hour one.
2. **Check for the peer before timing anything.** `ps aux | grep "[p]ytest"`, and read the checkout
   path on each hit. A peer session is invisible to `git status` here because it is a separate
   clone rather than a worktree.

`pytest-timeout` stays. It was added on a wrong hypothesis but it is the right instrument: it is
what lets a future session rule a hang in or out in five minutes rather than seventy.

## What this cost, and the generalisation

Roughly two hours of session #16, plus the opening of session #17. The generalisation is the one
this project keeps re-learning at a different altitude each time — after *the sample does not
exist* (ADR-063), *the SE is larger than the effect* (ADR-070), *the estimator was not pre-stated*
(ADR-074) and *the handoff's own count was wrong* (FINDING-013):

**Measure the environment before diagnosing the code.** Session #16 sampled the stuck worker, read
its stack, installed an instrument and wrote a hypothesis — all inside the process — without once
asking what else was on the machine. One `ps` would have answered it.
