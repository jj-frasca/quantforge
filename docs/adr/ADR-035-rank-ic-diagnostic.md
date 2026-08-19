# ADR-035: Every cross-sectional trial reports its rank IC — as a diagnostic, not a gate

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-024 (cross-sectional strategy dimension), ADR-033 (record the verdict, report it)

## Context
A cross-sectional strategy makes one claim: **its ranking of the universe is informative about
next-period returns.** Everything downstream — the dollar-neutral long/short legs, the realized
portfolio return series, the DSR/PBO/holdout gate applied to it — is a *consequence* of that claim.

QuantForge currently never measures the claim itself. `portfolio_returns` ranks each date, takes the
top and bottom quantiles, and hands the resulting return series to the same `GraduationGate` a
single-name strategy faces. That is a sound end-to-end test, but it is blind to a specific and
common failure: **a long/short portfolio can post a respectable Sharpe while the ranking carries
essentially no cross-sectional information**, because at a 0.2 quantile over ~50 names the P&L is
driven by ~10 positions per leg. A couple of names doing the work is a concentration story, not a
factor — and the two are indistinguishable from the portfolio return series alone.

The standard diagnostic for exactly this is the **information coefficient**: the per-date Spearman
rank correlation between the signal cross-section at *t* and asset returns from *t* to *t+1*. Its
summary statistics — mean IC, IC standard deviation, the IC information ratio (mean/std), and the
t-statistic (IR·√periods) — are how factor research reports whether a signal ranks. Grinold's
fundamental law, IR ≈ IC·√breadth, then gives an independent consistency check: a large realized
Sharpe on a small universe with a near-zero IC is a red flag, not a discovery.

This matters more now than it would have last month. ADR-033 established that 0 of 40 single-name
graduates clear the universe-deflation bar. When the cross-sectional dimension does eventually
produce a graduate, "is this a factor or is it two lucky names" is the first question anyone
competent will ask, and the pool currently cannot answer it.

## Decision
**Compute rank IC for every cross-sectional trial and record it on the trial. Do not gate on it.**

- `rank_ic(signals, prices)` returns the per-date Spearman correlation between the signal
  cross-section and the **next** bar's asset returns. Causality matches `portfolio_returns`
  exactly: rank on *t*, realize *t+1*. A date with fewer than two ranked names, or with a constant
  signal (zero variance, so the correlation is undefined), yields no IC and is dropped rather than
  counted as zero — recording "no information" for "not measurable" would bias the mean toward the
  null.
- `summarize_ic(series)` returns mean, std, IR, t-statistic, hit rate (share of dates with IC > 0)
  and the period count.
- The cross-sectional search has until now reused the single-name `lab.experiment.Trial`. It gains
  a `CrossSectionalTrial(Trial)` subclass carrying a nullable `ic` summary, populated by
  `run_cross_sectional_search` alongside the existing DSR / PBO / stability numbers. A subclass
  rather than a field on `Trial`, so a cross-sectional-only concept does not leak into the
  single-name model that the whole research pool is built on.

### Why a diagnostic and not a gate
Adding an IC floor to the graduation criteria would change what graduates. That is a threshold
change, and charter §4 permits one only on argued methodology with evidence — of which there is
currently none, because no cross-sectional experiment has ever had an IC computed. The honest
sequence is: measure first, accumulate a distribution, then argue for a floor in its own ADR if the
evidence supports one. This mirrors ADR-033's stance on the deflation verdict: record it, report it
prominently, and set an explicit trigger for promoting it to a gate.

**Trigger for revisiting:** once ≥50 cross-sectional trials carry an IC, compare the IC
distribution of gate-passing trials against gate-failing ones. If passing trials show no better IC,
that is evidence the portfolio-level gate is admitting concentration stories, and an IC floor
belongs in the gate.

## Alternatives considered

- **Gate on IC now.** Rejected: a threshold invented before any measurement is exactly the kind of
  number that gets quietly tuned later. Measure first.
- **Pearson correlation instead of Spearman.** Rejected: the signals are already cross-sectionally
  ranked or z-scored, and returns are fat-tailed. Rank correlation is what the ranking claim
  actually is, and it is robust to the outlier returns that would dominate a Pearson estimate.
- **IC computed only on the holdout.** Rejected: the in-sample IC series is what has enough periods
  to estimate a t-statistic, and IC is not being used to select anything — so there is no
  selection bias to protect against here. The holdout's job is unchanged.
- **Report IC per quantile bucket (a full quantile-spread table).** Genuinely more informative and
  the natural next step, but it multiplies the stored payload per trial in a pool that just hit
  GitHub's file-size wall (ADR-032). One scalar summary first.
- **Newey-West adjusted IC t-statistic.** The IC series is autocorrelated when the signal is slow
  (a 126-day momentum signal barely changes day to day), so the plain t-stat overstates
  significance. Real, and worth doing — but it is a second decision with its own lag-selection
  question, and the plain t-stat is not *wrong*, it is optimistic in a documented direction. Noted
  here so the number is not read as more precise than it is.

## Consequences

- Every cross-sectional trial gains a small IC summary; the pool payload grows by ~6 floats/trial.
- The cross-sectional hunt driver prints IC next to DSR, so a scheduled run says whether its
  factors rank at all — currently the most useful thing that dimension could report. The same two
  numbers are surfaced per trial by `GET /api/v1/cross-sectional` and in the dashboard's
  cross-sectional table, so the answer is visible without reading a workflow log.
- `CrossSectionalTrial.ic` is nullable, so trials persisted before this ADR still validate and are
  honestly marked "not measured" rather than backfilled.
- The t-statistic is optimistic under autocorrelated signals (see above). It is a screening
  diagnostic, not an inferential claim.

## Reversal
Drop `ic` from `CrossSectionalTrial` (or the subclass entirely, reverting `trials` to `list[Trial]`),
drop `ic_mean`/`ic_t_stat` from the endpoint view and the two dashboard columns, and delete
`cross_sectional/ic.py`. Nothing selects, gates, or
sizes on it, so removing it changes no verdict anywhere in the system.
