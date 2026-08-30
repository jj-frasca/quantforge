# ADR-068: Judge the out-of-sample diagnostic as excess over buy-and-hold

- **Status**: Accepted
- **Date**: 2026-08-30
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-064 (matched-history null comparison), ADR-051 (finalist OOS diagnostics),
  ADR-038 (walk-forward efficiency)
- **Relates to**: ADR-036/037 (null-model calibration), ADR-061 (the band gap was the benchmark)

## Context

ADR-064 made the real-vs-null comparison honest about *history* and reported its verdict on the
raw walk-forward OOS Sharpe: the matched pool's median is **+0.542** against the bootstrap:SPY
null's **+0.652**. The real pool scoring *below* a null with no edge by construction is the kind of
result that invites an explanation about the search being bad. **It has a much duller cause, and it
is measurable without running anything: the diagnostic is denominated in the drift of whatever
series it was computed on.**

Measured 2026-08-30 (session #13). "Underlying Sharpe" is `mean/std × √252` of the daily returns
the finalist was searched over — for the nulls, of the process that generates them; for the pool, of
the symbol itself. It is buy-and-hold, computed exactly as `walk_forward._sharpe` computes a
strategy's:

| side | underlying Sharpe | finalist walk-forward OOS median | excess |
|---|---|---|---|
| `iid_normal` null, 5,400 bars | **0.397** (analytic: drift 0.0003 / vol 0.012) | **+0.414** | **+0.017** |
| `iid_normal` null, 7,400 bars | 0.397 | +0.416 | +0.019 |
| `bootstrap:SPY` null, 5,400 bars | **0.650** (SPY 1993-01-29→2026-08-28, 8,453 bars) | **+0.652** | **+0.002** |
| `bootstrap:SPY` null, 7,400 bars | 0.650 | +0.622 | −0.028 |
| **real pool, matched cohort (5,445 bars)** | **0.546** (median of a 39-symbol sample) | **+0.542** | **−0.004** |

**Every row's finalist out-of-sample Sharpe is its own underlying's buy-and-hold Sharpe, to within
±0.03.** Two of these are nulls with zero exploitable structure by construction, and the level they
produce is not zero — it is the drift the generator carries. The gap ADR-064 reported is therefore
almost exactly the gap between SPY's 33-year drift (0.650) and the median pool symbol's over its own
window (0.546). It says nothing about the search on either side.

Read the other way, this is the cleanest statement of gate honesty the project has: what the search
adds out-of-sample, over holding the same series across the same windows, is **+0.002 to +0.019 on
data with no edge and −0.004 on real symbols** — indistinguishable from zero everywhere, which is
what a null must look like and, on this pool, what the real thing looks like too.

The real-side number is a sample, and the ADR does not lean on it as the final statistic: 39 of a
random 40 symbols (seed 7, AVB unfetchable) of the 487 in the matched cohort, over each symbol's
last 5,445 bars rather than over the walk-forward test blocks exactly, with the pool median taken
over 2,427 experiments rather than 487 symbols. It is decisive about the *confound* — a 0.10 gap
attributed to selection is a 0.10 gap in drift — and that is why the paired number belongs in the
record instead of an estimate of it.

## Decision

**Score buy-and-hold across the same walk-forward test blocks as the strategy, persist it, and
report the real-vs-null comparison on the excess as well as on the raw statistic.**

1. `walk_forward_evaluate` takes an optional `benchmark` series of per-bar returns and reports
   `mean_oos_hold_sharpe` — the same mean-over-splits of the same annualized Sharpe, on the same
   test indices. Pairing it structurally is the point: a benchmark computed over a different window
   is the error this ADR exists to remove.
2. `ValidationEngine.validate` passes the close-to-close returns of the frame it was handed, and
   `run_search` records the result once per `Experiment` as `walk_forward_hold_sharpe`. It is one
   number per experiment, not per trial, because the splits and the window are shared by every
   family in a search by construction.
3. `calibrate_gate` collects the same value per null symbol into
   `NullCalibration.walk_forward_hold_sharpes`, so the null side of the comparison carries its own
   benchmark rather than borrowing the pool's.
4. `pool_report` prints an **excess** row beside each existing raw row, with the same verdict rule
   ADR-064 fixed (real median vs null p95) applied to the excess. **The raw row stays.** Changing
   the statistic a published verdict was quoted on, in place, is how a project loses the ability to
   be checked; both are printed and the excess is labelled as the drift-controlled one.
5. Every new field is nullable and reads as **not measured** where it is absent, per ADR-067. The
   pool and the null artifacts on disk predate all of them: the excess row is unmeasurable until
   the daily discovery re-searches and the null calibration is re-dispatched, and it must say so
   rather than print a zero excess it did not measure.

## Alternatives considered

- **Bootstrap the null from each real symbol's own bars.** The ideal drift control — the null then
  matches the pool symbol by symbol rather than in the median — but it costs one full null
  calibration per symbol (487 × a multi-minute search) and turns a property of the *gate* into a
  property of each name. Rejected on cost, and it answers a different question.
- **Subtract one market-wide drift constant from both sides.** Rejected: the sample's own spread
  (p25 0.42, p75 0.64, min 0.21, max 0.83) shows the pool's drift is heterogeneous, so a constant
  controls nothing for any individual row.
- **Print the underlying Sharpe as context and leave the comparison alone.** Rejected: the whole
  failure mode is a reader comparing +0.542 with +0.652 and concluding something about the search.
  The control has to be in the row being read, not in a footnote under it.
- **Lean on the gate's existing beat-buy-and-hold criterion.** It is a pass/fail for the finalist on
  the *locked holdout*; it does not make a walk-forward diagnostic comparable across two different
  underlying processes, which is what the null comparison needs.
- **Replace the raw comparison with the excess.** Rejected — see decision 5. ADR-064's verdict was
  published on the raw statistic and stays checkable on it.

## Consequences

- ADR-064's reported gap is reframed as a difference in drift, not in skill. **The verdict is
  unchanged**: neither statistic separates the pool from a no-edge surrogate, on either the raw or
  the excess form, and this ADR adds no graduate and moves no threshold.
- The project gains a statement it could not previously make: *the search's out-of-sample
  contribution over holding the same series is within ±0.02 of zero on both nulls.*
- Two artifacts must be regenerated before the excess row can be read: the pool (daily discovery,
  automatic) and the null calibration (one dispatch of `null-calibration.yml`, token-free).
- `walk_forward_evaluate` gains one Sharpe per split — negligible beside backtesting the grid it
  already scores.
- The same confound applies to the purged-CV row, which resamples the same underlying. This ADR
  covers the walk-forward statistic only, because purged-CV's folds are not a prefix-ordered
  benchmark window; extending it should be argued on its own terms.

## Measured (run 33287465013, committed `a61beb0`)

The null side is no longer an estimate. Both 7,400-bar nulls were re-dispatched hours after this
ADR was accepted, carrying the paired benchmark, 200 symbols per mode, 0 false graduates, all 16
shards green. The excess below is the **median of the per-symbol differences**, not the difference
of the medians:

| null (7,400 bars) | finalist OOS median | its own hold median | **paired excess** (median / mean) | excess p95 | corr(OOS, hold) | share beating hold |
|---|---|---|---|---|---|---|
| `bootstrap:SPY` | +0.622 | +0.652 | **−0.006** / −0.028 | +0.096 | **0.884** | 18.5% |
| `iid_normal` | +0.416 | +0.394 | **+0.000** / +0.012 | +0.325 | 0.652 | 36.0% |

Three things this settles that the estimate could only suggest:

1. **The paired excess is zero.** Not "small" — the median is −0.006 and 0.000 on 200 symbols each.
   The whole level of the OOS diagnostic under a null is the drift of the generated series.
2. **The finalist usually LOSES to holding.** On structure-free data the searched finalist beats
   buy-and-hold on the same windows 18.5% (bootstrap) and 36.0% (iid) of the time. It pays turnover
   costs for a signal that is not there, which is what should happen and had never been measured.
3. **The excess is a far tighter instrument.** The null band collapses: bootstrap p95 falls from
   **+0.968 raw to +0.096 excess**, a factor of ten. Under ADR-064's verdict rule a real pool must
   clear the null's p95, so the drift-controlled comparison is not merely unconfounded — it is an
   order of magnitude more sensitive. The raw comparison could only ever have detected an edge
   larger than the spread of market drift; this one cannot be satisfied by drift at all.

The `corr(OOS, hold) = 0.884` on the bootstrap null is the confound stated as one number: on data
with no exploitable structure by construction, 88% of the co-movement in the statistic the project
publishes is the underlying's own drift.

**Still not measured: the real side.** Every experiment in the pool predates
`walk_forward_hold_sharpe`, and the 5,400-bar nulls the current pool matches predate
`walk_forward_hold_sharpes`, so `pool_report.py` prints `NOT MEASURED` for the excess row and is
right to. It resolves as the daily discovery re-searches the universe at ADR-063's 7,400-bar window
— the same cohort these nulls were measured at. Do not quote a real excess before then; the
39-symbol sample in §Context is evidence about the confound, not a result.

## How to reverse

Drop the `benchmark` argument, the three persisted fields and the excess row. The raw comparison,
its verdict rule and every published number are untouched by this ADR in either direction.
