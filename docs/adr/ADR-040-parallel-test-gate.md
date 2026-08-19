# ADR-040: Run the backend gate in parallel, and require order-independent tests

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1 / §2 item 5)

## Context
`make check` is mandatory before every commit (`AUTONOMY_CHARTER.md` §3, "no exceptions"), and it
is the single largest consumer of an autonomous session's wall clock — which is the binding budget,
not tokens (session #2 retro, 2026-08-18). Measured on this machine, 2026-08-19:

| run | wall clock |
|---|---|
| `pytest -m "not live and not integration"` (no coverage) | 5 min 13 s |
| the same with `--cov=app` (i.e. `make test`) | 8 min 45 s |
| with `-n auto` and coverage (the new `make test`) | **4 min 01 s** |

A session that commits granularly — which the charter also requires, because it is killed without
warning — pays that cost once per commit. This session ran the gate eleven times: roughly 95
minutes, over half its productive wall clock, spent waiting.

(A first measurement via `uv run --with pytest-xdist` read 5 min 58 s; that figure carried uv's
per-invocation resolution of a not-yet-installed extra. With the dependency in the dev group, the
gate's own run is 4 min 01 s. The table reports the installed number, which is the one that will
actually be paid.)

The suite is also unusually top-heavy: `test_cross_sectional_search.py` alone accounts for ~150 s
across 8 tests, and two single tests cost 62 s and 36 s. Those are legitimate — they run real
cross-sectional searches — but they mean the serial suite is mostly one core waiting.

## Decision
**Add `pytest-xdist` and run the backend test target with `-n auto`.**

- `make test`, and therefore `make check` and `make check-all`, distribute across cores.
- Coverage is unaffected: `pytest-cov` combines the workers' data, and the totals were identical
  (99.98%, same single miss) across serial and parallel runs.
- `-n auto` rather than a fixed count, so it adapts to a 2-core CI runner and to this Mac alike.
- `make test-live` and `make test-integration` stay serial: live tests share an external
  rate-limited API, and DB-backed tests share one database.

### The constraint this creates, stated plainly
Parallelism makes **test order and test isolation load-bearing**. Any test that writes a fixed path,
mutates module state, or depends on running after another test can now fail — or, worse, pass
locally and fail in CI at a different worker count. Every test must use `tmp_path`/fixtures for
files and must not depend on execution order. This ADR is where that requirement is recorded;
`.claude/rules/test-files.md` carries it for anyone editing tests.

**Evidence, and its limit:** the full suite was run twice under `-n 8` (once with coverage, once
without) and passed identically both times. Two green runs are not a proof of order-independence —
they are the evidence available, and the honest statement is that a latent ordering dependency
would show up as an intermittent failure rather than being ruled out here. The mitigation is cheap:
if a test fails only under `-n auto`, run it with `-p no:randomly -n 0` to confirm, and fix the
shared state rather than pinning the test.

## Alternatives considered

1. **Leave it serial.** No new dependency and no isolation constraint. Rejected: a third of the
   gate's wall clock, on the resource the charter names as the binding one, is a large recurring
   cost to decline.
2. **Speed up the slow tests instead.** `test_cross_sectional_search.py` re-runs a full search per
   test; module-scoped fixtures would cut it. Better in principle and not exclusive with this —
   but the tests search *different* strategy sets, so the sharable work is limited, and it is a
   refactor of the tests whose correctness is the thing being relied on. Parallelism is the
   change with the better risk-to-payoff ratio; the fixture work remains available afterwards.
3. **Only parallelize in CI, not locally.** Rejected: it would make the local gate and the CI gate
   differ, which is exactly how an ordering bug gets discovered by CI instead of by the author.
4. **Drop coverage from the pre-commit gate.** Cheapest of all (3.5 minutes) and clearly wrong —
   coverage not dropping is a standing project rule (CLAUDE.md rule 5).

## Consequences
- Roughly **4 min 45 s off every backend gate** (8:45 -> 4:01), locally and in CI.
- One new dev dependency, `pytest-xdist` (free, no service, no runtime dependency).
- Tests must be order-independent and must not share fixed paths. Recorded in
  `.claude/rules/test-files.md`.
- Failure output interleaves across workers; `-n 0` reproduces serially when debugging.

## Reversal
Drop `-n auto` from the `test` target in the `Makefile` and remove `pytest-xdist` from the dev
dependency group. Nothing else depends on it.
