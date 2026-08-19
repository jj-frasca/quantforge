# ADR-037: Publish the null calibration as a sharded, scheduled cloud measurement

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-036 (null-model gate calibration), ADR-026 (sharded cloud discovery),
  ADR-030 (single writer per generated data file)

## Context
ADR-036 built the instrument — `calibrate_gate` runs the unmodified search + gate over price frames
with no edge by construction and reports the false-graduation rate — and then explicitly deferred
the expensive part: *"the large run is a driver script, like every other expensive thing in this
repo."* The only number ever produced is the CI unit test's: **6 null symbols, 3 strategies**. That
pins the harness's mechanics. It is not a measurement. A Type-I error estimated from 6 draws has a
95% interval covering roughly 0–46%; it cannot distinguish an honest gate from a leaky one.

Meanwhile the claim that number is supposed to support is the project's headline claim. The live
pool says 0 of 40 graduates clear the ADR-018 bar (`scripts/pool_report.py`, 2026-08-19). That is
consistent with a well-calibrated gate *and* with an over-tight one; ADR-036 already says so. The
null run is the experiment that separates them, and it has not been run at a size that resolves
anything.

The obstacle was never conceptual, it was compute: one full-catalog search over a 3000-bar frame
costs ~23 s of single-core CPU, so a 200-symbol calibration in both null modes is a couple of
CPU-hours. That is exactly the resource this project already has for free — a public repo with
unlimited GitHub Actions minutes, which ADR-026 already exploits for daily discovery.

Null symbols are **independent by construction**, so unlike the cross-sectional hunt (which needs
every name in one panel) this workload shards perfectly.

## Decision
**Shard the null calibration across a GitHub Actions matrix, merge the shards into one calibration
at the combined N, publish the result to `data/null_calibration/`, and re-run it on a schedule
and on demand. Change no threshold in this ADR.**

Three parts:

1. **`NullGraduate` + `merge_calibrations`** in `app/research/lab/calibration.py`. A shard cannot
   report a final answer: the ADR-018 universe-deflation bar is a function of the *total* number of
   symbols searched, so a graduate that clears its shard's 25-symbol bar may not clear the merged
   200-symbol bar. Each shard therefore records, per false graduate, the holdout Sharpe and holdout
   length that the bar must be recomputed against, and `merge_calibrations` recomputes
   `deflation_bar` and `n_clear_deflation_bar` at the merged N. Merging refuses to combine shards
   built under different `gate_config_version`s — a rate is a property of one gate config (ADR-036).
2. **`scripts/null_calibration.py --shard I/N --out PATH`** writes a shard's `NullCalibration` as
   JSON, and `scripts/consolidate_null_calibration.py` merges a directory of them and prints the
   headline. Seeds are derived from the global symbol index, not the shard index, so the union of
   shards is exactly the same set of null symbols a single 200-symbol run would produce — the
   sharding is an execution detail with no effect on the measurement. (In `bootstrap` mode each
   shard fetches the source symbol independently, so exact reproduction additionally requires
   those fetches to return the same bars; a stale-by-one-bar shard is still a valid null, just
   not a bit-identical one.)
3. **`.github/workflows/null-calibration.yml`** — a 2x8 matrix (both null modes x 8 shards),
   monthly and on `workflow_dispatch`. Each mode is consolidated **separately** into
   `data/null_calibration/<mode>.json`; merging across modes is refused in code, so the two numbers
   can never be silently pooled. The workflow is the **sole writer** of that directory (ADR-030) —
   no local or session writer may commit into it, and a local run should write to a scratch path.

**Cadence: monthly, plus manual dispatch.** The result is a property of a `GateConfig`, which
changes rarely. `gate_config_version` is recorded in the artifact, so a stale number is detectable
rather than silently trusted, and any session that changes the gate dispatches a re-run.

## Alternatives considered
- **Run it locally in an autonomous session.** ~2 CPU-hours against a 5-hour session wall clock that
  is the binding budget constraint (session #2 retro). It also would not be repeatable when the gate
  changes, which is the whole point of ADR-036's last consequence. Cloud minutes are free; session
  wall clock is not.
- **Run it in CI on every push.** Rejected in ADR-036 and still rejected: hours per push to
  re-measure a quantity that only moves when `GateConfig` moves.
- **Average the shards' `false_graduation_rate`s.** Wrong for the deflation count and needlessly
  wrong for the rate: the rates are over unequal denominators when a shard has unsearchable symbols,
  and the deflation bar is not linear in N. Merge the counts and recompute.
- **Report each shard separately and eyeball them.** A 25-symbol Type-I estimate is as uninformative
  as the 6-symbol one; the point of the exercise is a single number with a usable interval.
- **Store the result in the research pool.** Forbidden by ADR-036 — null experiments must never
  inflate the MinTRL denominator or reach the leaderboard. `data/null_calibration/` holds
  summary-only artifacts carrying no `Experiment` objects.

## Consequences
- The project can state a measured, seeded, reproducible false-graduation rate for its whole
  pipeline at a sample size that supports a confidence interval, and refresh it whenever the gate
  changes. This is the strongest available answer to "how do you know the gate is honest?".
- A new generated data directory, `data/null_calibration/`, with exactly one writer.
- If the measured rate comes back materially above nominal, that is evidence to **tighten** the gate
  in a follow-up ADR citing this number. Charter §4 stands: it is never evidence to loosen one.
- Merging is refused across gate config versions, so a gate change cannot silently be papered over
  with stale shards.

## Reversal
Delete `.github/workflows/null-calibration.yml`, `scripts/consolidate_null_calibration.py`, the
`--shard`/`--out` flags, and `merge_calibrations`/`NullGraduate`. `calibrate_gate` and ADR-036's
harness are untouched and keep working standalone. Nothing in the hunt, gate, pool or paper book
reads any of it.
