# ADR-075: Size the excess comparison by symbol-clustered bootstrap

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #15 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-072, whose "open question this raises, deliberately not decided here" this closes
- **Relates to**: ADR-064 (matched-history comparison), ADR-068 (the excess statistic),
  ADR-070/074 (state the standard error, and the estimator, before the threshold)

## Context

ADR-072 measured the drift-controlled row for the first time — real median **−0.125** against
bootstrap-null **−0.006** and iid-null **+0.000** — and reported `does not separate`, because
−0.125 lies inside the nulls' p5 of −0.233 / −0.251. It also recorded, without acting on it, that
**this is a comparison of two different quantities**: the real side is a *median of 77*, the band is
over *individual null draws*. A band over single draws is the right yardstick for asking "could one
symbol look like this by chance"; it is the wrong one for "is the pool's central tendency different
from the null's", which is the question the row is actually asked.

ADR-072 declined to rescale it on the spot for two reasons, both still valid. First, ADR-070's
meta-lesson: a criterion is not re-scaled after seeing the number it would act on. Second, the
obvious rescaling is wrong in a way that would overstate the result — the 77 excesses are not 77
independent draws. They come from **66 symbols** (some searched more than once), over **one
overlapping calendar window**, with `fifty_two_week_high` the finalist in 30 of 77.

## Full disclosure, because it decides how much this ADR is worth

**The point estimate is already known, and the expected outcome of the procedure below is a
separation.** What is being pre-registered here is therefore the **procedure and the reporting
commitment**, not a blind test: the resampling scheme, its seed, its two-sidedness, and the promise
to report whatever it returns beside the limitation it does not cover. Anyone reading this should
discount it accordingly. It is still worth doing, because the alternative on the page today — a
median compared against a single-draw band — answers a question nobody asked, and because the
scheme is fixed in advance of the interval, which is the part that could otherwise be shopped.

## Decision

The drift-controlled row additionally reports a **symbol-clustered bootstrap interval for the
difference between the two sides' medians**.

1. **Resampling.** Draw the real side by SYMBOL with replacement (66 clusters, all of a resampled
   symbol's experiments enter together), and the null side by draw with replacement (each null
   symbol is an independently generated series, so draws are its natural unit). Take each side's
   median, take the difference, repeat **B = 20,000** with **seed 7** — the same constants
   `compare_search_windows` already uses, so one project has one bootstrap.
2. **Statistic and reading.** `difference_ci_low` / `difference_ci_high` are the 2.5th and 97.5th
   percentiles of that difference. **The two sides are distinguishable when the interval excludes
   zero**, in whichever direction; the sign is read off `real_median − null_median`.
3. **Scope.** Emitted on the centered row only, and `difference_n_clusters` is reported beside it so
   the interval is never read without its sample. The raw rows get nothing: ADR-068 measured that
   their level is each side's own drift, so an interval around that difference sizes a drift gap.
4. **The existing verdict is not replaced.** `real_exceeds_null_p95` / `real_below_null_p5` and
   their single-draw band stay exactly as they are, and stay the headline verdict. ADR-068's rule
   holds — **a published verdict is not restated on a new statistic in place**; the interval is
   reported beside it and each says what it sizes.

## What this deliberately does NOT control for, and it matters

The 66 symbols were all searched over **one shared calendar window**. A symbol-clustered bootstrap
removes within-symbol repeats and symbol-level heterogeneity; it does **not** remove cross-sectional
correlation — 2008 and 2020 happened to all of them at once, and a strategy family that failed
across the market in one regime fails on every symbol together. The interval this ADR produces is
therefore a **lower bound on the true width**, and must be quoted that way.

Removing that confound needs a null that has the same dependence structure: a bootstrap null drawn
as a **correlated panel** rather than 200 independent series. That is a real piece of work and it
belongs in its own ADR — it changes what `null_calibration.py` generates, not how a row is read.

## Alternatives considered

1. **Compare the real median to the sampling band of the null's median at n = 77.** Simpler, and it
   is the arithmetic ADR-072 recorded (SE ≈ 0.016 → about 7 SE). Rejected: it assumes the real side
   has the null's dispersion and independence, and it has neither.
2. **A block bootstrap over calendar time.** The right instrument for the confound named above, but
   the pool stores one scalar per experiment, not a time series of excesses, so there are no blocks
   to resample. It would require persisting per-fold excesses — a schema change to buy an interval,
   which is the wrong order.
3. **Replace the single-draw band with the clustered interval.** Rejected under ADR-068's rule
   against restating a published verdict on a new statistic in place. Both are reported; each
   answers a different question, and the page says which.
4. **Do nothing until the pool doubles.** The sample grows every weekday and the interval will
   narrow on its own — but the mis-sized comparison would keep printing in the meantime, and the
   number it hides is the project's most quotable result.

## Consequences

- The project can state whether its search's drift-controlled contribution is distinguishable from a
  no-edge surrogate's using a comparison of like with like, and can state exactly what that comparison
  still does not cover.
- Two intervals now appear on one row. The panel and the CLI must label which question each answers,
  or the row becomes less honest than the one it replaced.
- A correlated-panel null becomes the obvious next piece of methodology, with a named reason.

## Reversal

Drop `difference_ci_*` and `difference_n_clusters`. The row returns to comparing a median against a
band over single draws, which is the state ADR-072 flagged and did not fix.

## Measured (2026-08-31, same session) — both intervals exclude zero

`PYTHONPATH=. uv run python scripts/pool_report.py` from `backend/`, on the same 77 experiments over
**66 symbol clusters** at 7,345 bars that ADR-072 read:

| null (7,400 bars) | real median | null median | difference | 95% CI, symbol-clustered | reading |
|---|---|---|---|---|---|
| `bootstrap:SPY` | −0.125 | −0.006 | **−0.119** | **[−0.215, −0.061]** | excludes zero |
| `iid_normal` | −0.125 | +0.000 | **−0.125** | **[−0.218, −0.063]** | excludes zero |

**Read as the procedure allows and no further: the drift-controlled contribution of the search on
real symbols is distinguishable from what the same search contributes on data with no edge by
construction, and it is distinguishable in the NEGATIVE direction.** The search subtracts about
0.12 Sharpe more on real data than on structure-free surrogates, where it subtracts approximately
nothing.

Three qualifications travel with that sentence and must not be dropped from it:

1. **The interval is a lower bound on its own width.** The 66 symbols share one calendar window, so
   cross-sectional correlation is not resampled away. A correlated-panel null is the fix and it is
   not this ADR.
2. **The single-draw verdict is unchanged and still says `does not separate`.** −0.125 is inside
   both nulls' p5. The two statements are not in conflict: one asks whether a single symbol could
   look like this (it easily could), the other whether the pool's centre differs from the null's
   (it does). The report prints both, labelled.
3. **This was not a blind test.** The disclosure section above stands: the point estimate was known
   before the scheme was fixed. What the scheme buys is that the interval could not be shopped, and
   the outcome is the one the ADR said to expect.

The most useful thing it changes: **the honest headline is no longer "the search does not separate
from a no-edge surrogate" but "the search separates from a no-edge surrogate in the wrong
direction."** That is a stronger claim about the pipeline's honesty than the neutral one it
replaces, and it is the sharpest evidence yet that the in-sample argmax fits structure that does not
persist.
