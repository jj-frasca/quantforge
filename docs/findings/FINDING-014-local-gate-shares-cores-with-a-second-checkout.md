# FINDING-014: the local gate was never hung — it was sharing eight cores with a second checkout

- **Status**: **RESOLVED, and PARTLY WRONG on the way there. Read §Correction and §Resolved before
  quoting anything above them.** The contention is real and measured; the causal claim in the title
  is not the reason the gate fails to finish. The real cause is named in §Resolved and is fixed.
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

## Correction (2026-08-31, hours after the above)

The run that followed this finding finished its own timing line, and it overturns the diagnosis:

```
make check PYTEST_WORKERS=6   476.31s user  5.37s system  10% cpu  1:16:13.84 total
6 workers [1391 items]
... F at ~20% ... F at ~25% ...
.................................[gw4] node down: Not properly terminated
F
replacing crashed worker gw4
........................................................   <- and there it stays
```

**476 seconds of user CPU — eight minutes, which is CI's 8m36s almost exactly — spread over 76
minutes of wall clock at 10% CPU.** The suite is not slow and it is not CPU-starved. It is *idle*.
The peer checkout's gate had exited half an hour before this run stalled, so by the end there was no
contention left to blame.

Per-process CPU deltas over a 30-second window, taken while the run was "stuck", say the same thing:
five of the six workers were flat to the hundredth of a second, one was live, and the one `ps` had
been reporting at 100% was blocked in `_io__Buffered_read` on its xdist channel — `ps` %CPU is a
decaying average and it was stale. Sampling the "pegged" worker showed a main thread parked in
`_Py_read`, waiting for the master to send it work.

**What actually happens:** a test kills its worker (`node down: Not properly terminated`), xdist
replaces the worker, and the run then waits forever on a worker that never reports back. That is a
stall around a crashing test, not a hang inside one, and not starvation.

### What survives from the original finding

- The two-checkout contention is real and was measured: `~/claude-work/quantforge-codex` runs the
  same `-n auto` gate, 16 workers per clone, load average 36.9 on 8 physical cores. It inflates
  wall time severely and it is worth avoiding.
- `PYTEST_WORKERS` is worth keeping for that reason. It is not a fix for the stall.
- "Measure the environment before diagnosing the code" still stands. So does its complement, which
  this correction is: **measure the environment and then keep measuring, because one `ps` snapshot
  supports a story that a CPU delta over 30 seconds destroys.** The first measurement was right
  about what it saw and wrong about what it meant.

### Resolved (2026-08-31, session #18) — one `iterrows()` in a production hot path

**The test is `tests/unit/test_cross_sectional_forward.py::test_score_forward_is_truncation_invariant_no_lookahead`.**
A serial run (`-p no:xdist --timeout=90`) named it in one line, because without xdist a timeout is
reported instead of taking a worker down with it. The traceback lands in the same frame every time:

```
tests/unit/test_cross_sectional_forward.py:284  trunc_equity = score_forward(pos, truncated)
app/research/cross_sectional/forward.py:116     fwd = _factor_returns(position, panel)[forward_mask]
app/research/cross_sectional/forward.py:88      portfolio_returns(signal, panel, ...)
app/research/cross_sectional/engine.py:30       long_short_weights(signals, quantile)
app/research/cross_sectional/panel.py:22        for date, row in signals.iterrows():
pandas/core/frame.py:1586  iterrows -> Series.__init__ -> data.copy()
+++ Timeout +++
```

`long_short_weights` walked the signal panel with `DataFrame.iterrows()`, which rebuilds and copies
a Series per date, and a Hypothesis `@given(cut=st.integers(1, 200))` property calls `score_forward`
twice per example. **This was never only a test's cost — every cross-sectional backtest ranks
through this function.**

The fix is to rank the whole frame at once (`DataFrame.rank(axis=1)` plus two row-wise comparisons)
rather than per date. Measured on a 2,000 x 200 panel: **3.664s -> 0.053s, a 69x speedup**, with the
two implementations agreeing exactly across 1,500 randomised panels (ragged NaN masks, duplicate
columns to exercise tie-breaking, quantiles 0.1/0.2/0.25/1-3/0.5). The test file that could not
finish inside 300s now runs in **17.6s end to end**.

**Why CI was green while this machine was not: it is the same slow code on both.** CI squeaked in
under the 300s per-test timeout and this x86-64 mac did not. Nothing about the defect was
environment-specific — only which side of the timeout it landed on. So the gate was honest and the
code was slow, and raising the timeout would have been the wrong fix: it would have bought a green
local gate and kept the 69x in the backtester.

**And that is the full chain to "the suite no longer finishes":** under `-n auto` the timeout kills
the worker (`node down: Not properly terminated`), xdist replaces it, and the master then waits
forever for a worker that never reports. One `iterrows()`, five sessions of symptoms.

**The two unnamed `F` failures are also accounted for** and were never assertion failures: they are
this same timeout firing on whichever worker drew the slow property test, which is why they moved
position between runs. Nothing else in the suite exceeded the timeout in the serial run.

### Still open

~~Which test crashes its worker~~ and ~~the two unnamed `F` failures~~ are both answered in
§Resolved above. What remains is a property of the tooling rather than of this suite:

- **xdist turns a per-test timeout into an indefinite stall.** The worker dies, `replace` brings a
  new one up, and the master never reports. Any future test that exceeds `--timeout` will present
  as "the gate hangs" again rather than as a named failure. The instrument that shortcuts the
  investigation is a serial run — `pytest -p no:xdist --timeout=90 -rf` — which names the offender
  in minutes; `--faulthandler-timeout=N` is the fallback if a native call is holding the GIL.
