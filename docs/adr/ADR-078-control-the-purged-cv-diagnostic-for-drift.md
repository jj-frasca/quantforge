# ADR-078: Control the purged-CV diagnostic for drift, the way walk-forward already is

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #18 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-068 (excess over buy-and-hold — this ADR overturns its deferral of purged CV),
  ADR-039 (purged CV with a lookback embargo), ADR-064 (matched-history null comparison)
- **Relates to**: ADR-076 (the same subtraction changed an answer), ADR-072 (read the excess row
  two-sided), ADR-075 (cluster the excess comparison by symbol), ADR-067 (absent means not measured)

## Context

ADR-068 established that the walk-forward OOS Sharpe is **denominated in the drift of the series it
was computed on** — on both nulls the finalist's median lands within 0.02 of that generator's own
buy-and-hold Sharpe, and `corr(OOS, hold) = 0.884` on `bootstrap:SPY`. It therefore scored
buy-and-hold across the same test blocks, published the excess beside the raw row, and showed the
drift-controlled band is roughly **ten times tighter** (bootstrap p95 +0.968 raw → +0.096 excess).

ADR-068 deliberately stopped at walk-forward. Its Consequences section says so:

> The same confound applies to the purged-CV row, which resamples the same underlying. This ADR
> covers the walk-forward statistic only, because purged-CV's folds are not a prefix-ordered
> benchmark window; extending it should be argued on its own terms.

**These are its own terms, and two things have changed since.**

**First, the deferral's stated reason does not survive inspection.** "Not a prefix-ordered benchmark
window" is a fact about *selection*, not about the benchmark. Purged CV's training rows include
indices after its test block, so the config it picks is non-causal — that is the technique's
declared trade (ADR-039). But buy-and-hold has no config to pick. Scoring it on a fold's test
indices is the identical operation `walk_forward._sharpe(benchmark[test_idx])` performs, and it is
causal on both sides regardless of what the strategy's selection saw. Nothing about fold ordering
makes `mean(sharpe(benchmark[test_idx]))` a different statistic than it is under walk-forward.

If anything the purged-CV control is the **cleaner** of the two. `purged_kfold_splits` tests every
index exactly once, so the union of its test blocks is the whole searched window and the hold
control is the underlying's own Sharpe over precisely the history the search saw, chopped into k
pieces. Walk-forward's test blocks skip the first train block, so its control covers a suffix.

**Second, ADR-076 measured what leaving a statistic uncontrolled costs, on real data.** Over the
same frozen 200 symbols, the raw OOS window delta is **−0.037 [−0.061, −0.008] — excluding zero** —
and subtracting what holding the same series across the same windows earned collapses it to
**−0.008 [−0.055, +0.022], covering zero**. Same symbols, same searches, opposite conclusions. An
uncontrolled row does not merely read imprecisely; it can read as a result.

So the project currently publishes, in `compare_with_null`, one row per null mode on the raw
purged-CV Sharpe — `+0.584` real against `+0.661` / p95 `+1.003` bootstrap (ADR-064) — with no
drift control and no plan to acquire one, next to a walk-forward row that has both. **That is the
one remaining published headline in this project quoting a surrogate whose control has never been
measured**, which is the audit session #17's handoff asked for. Nothing else qualifies: ADR-055 and
ADR-061 charged the capture ratios their cost and their achievable oracle, ADR-060's category lead
is differenced within symbol, and ADR-075's clustered interval is already built on the controlled
statistic.

## Decision

**Extend ADR-068's control to purged CV, by the same mechanism, and report it the same way.**

1. `purged_cv_evaluate` takes an optional `benchmark` of per-bar returns and reports
   `mean_oos_hold_sharpe` — the mean over folds of the same annualized Sharpe on the same test
   indices. It is averaged over the **kept** folds only: a fold whose training set was purged away
   is dropped rather than scored (ADR-039), and a benchmark averaged over folds the strategy was
   never scored on would not be the paired quantity.
2. `ValidationEngine.validate` passes the same `hold_returns` it already computes for walk-forward.
   One benchmark, both diagnostics, one window — the pairing stays structural, which is the whole
   point of ADR-068 decision 1.
3. `run_search` records it once per `Experiment` as `purged_cv_hold_sharpe`, and `calibrate_gate`
   collects it per null symbol into `NullCalibration.purged_cv_hold_sharpes`, so the null side
   carries its own benchmark rather than borrowing the pool's.
4. `compare_with_null` emits a **`purged-CV excess`** row beside the existing `purged-CV` row, on
   the same footing as `walk-forward excess`: paired per symbol, clustered by symbol for the
   interval (ADR-075), read two-sided (ADR-072), and refused below `MIN_MATCHED` clusters.
   **The raw purged-CV row stays** — ADR-068 decision 4's rule, unchanged: a published verdict is
   not restated on a new statistic in place.
5. Every new field is nullable and absent reads as **not measured**, never as zero excess
   (ADR-067). Every artifact on disk predates all of them, so the row is unmeasurable until the
   daily discovery re-searches and `null-calibration.yml` is re-dispatched, and it must say so.

**No threshold moves and nothing gates on either statistic** (ADR-039: purged CV is diagnostic
only). This ADR adds a control to a number the project already publishes.

## Alternatives considered

- **Leave it, and note the confound in prose beside the row.** Rejected for the reason ADR-068
  rejected the same option for walk-forward: the failure mode is a reader comparing +0.584 with
  +0.661 and concluding something about the search. A control that lives in a footnote is not
  applied by the person reading the row.
- **Replace the raw purged-CV row with the excess.** Rejected. ADR-064's verdict was published on
  the raw statistic and stays checkable on it, and two rows is how a later session can tell a drift
  effect from a search effect at a glance — which is exactly the contrast that made ADR-076 legible.
- **Reuse the walk-forward hold Sharpe as purged CV's control too.** Cheaper — no new field — and
  wrong: the two score different index sets (walk-forward's test blocks are a suffix, purged CV's
  are the whole window), so the difference would mix a drift correction from one window into a
  statistic measured on another. That is the confound this ADR removes, reintroduced.
- **Control by differencing the two diagnostics against each other** (purged CV minus walk-forward,
  already interpretable as a selection-leakage gap). Rejected: it removes drift only if both carry
  it identically, which is the assumption under test, and it destroys the level of both.
- **Wait for the pool to re-search before deciding.** Rejected on ordering: the field has to exist
  before a re-search can populate it. ADR-068 took four days to become measurable for exactly this
  reason, and the cost of that latency is why this one should not be deferred behind another
  artifact cycle.

## Consequences

- The purged-CV row acquires the same order-of-magnitude sensitivity gain ADR-068 measured for
  walk-forward, if the same mechanism holds — **which is itself the first thing the new row will
  test.** If purged CV's excess band does *not* collapse the way walk-forward's did, that is a real
  difference between the two diagnostics and worth its own finding.
- Two artifacts must regenerate before the row can be read: the pool (daily discovery, automatic)
  and the null calibration (one `null-calibration.yml` dispatch, token-free). Until then
  `pool_report.py` prints the row as not measured, and that is the correct output.
- `purged_cv_evaluate` gains one Sharpe per fold — negligible beside scoring the config grid it
  already backtests.
- The audit that produced this ADR is itself a consequence worth recording: **every other headline
  the project publishes was checked against the same question and found controlled.** If a future
  statistic is added, the check is "what does this number read on data with no edge by
  construction, and is that level subtracted?"

## Reversal

Delete `mean_oos_hold_sharpe` from `PurgedCVResult`, the `benchmark` argument from
`purged_cv_evaluate`, `Experiment.purged_cv_hold_sharpe`, `NullCalibration.purged_cv_hold_sharpes`,
and the `purged-CV excess` branch of `_excess_rows`. Every field is additive and nullable, so no
committed artifact becomes unreadable and no existing row changes value.
