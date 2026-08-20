# ADR-059: Record capture per catalog category — the winner is not always trading the planted edge

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-058 §Decision 3 (the next unit is the selection step), ADR-057 (finalist attribution)
- **Relates to**: ADR-045 (capture efficiency), ADR-055 (net oracle), ADR-042 (band-reversion horizons)

## Context

ADR-057's attribution showed that on fast band reversion the max-DSR search selects a **Trend**
strategy 68% of the time. A local probe over the same planted process (5 seeds × 5400 bars, reading
the per-family finalists that `Experiment.trials` already carries) shows what that costs:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| winning family's in-sample Sharpe | 0.816 | 0.792 | 0.766 | 0.723 | 0.779 | 0.670 |
| winning category | Trend | Trend | Trend | Combination | Mean Reversion | Trend |
| best **reverting** family | 0.374 | 0.469 | 0.582 | 0.618 | 0.779 | 0.540 |
| reverting ÷ winner | 46% | 59% | 76% | 85% | 100% | 81% |

**The winner's Sharpe is nearly flat (0.67–0.82) while the planted net oracle swings 1.24 → 2.21.**
A number that does not move with the planted edge is not measuring the planted edge. At half-life 1
the random-walk level carries 83% of return variance by construction, and `fifty_two_week_high` fits
*that* — scoring 0.816 while the best reverting family manages 0.374 and ranks 8th–17th of 34.

So ADR-045's capture ratio has a second defect, structurally the same as the one ADR-055 fixed on
its denominator. The numerator is "the best in-sample finalist", with no requirement that the
finalist trades the planted process at all. On the fast band cells the reported 31.6% is largely a
trend strategy's fit to the level; the reverting families' own share is ≈ 0.374 / 1.70 ≈ **22%**.
Every reading of those cells — including ADR-056's, which used them to justify adding a strategy —
has been made against a numerator that overstates expression of the thing actually planted.

## Decision

**Record the best finalist Sharpe *within each catalog category* on every power cell, and serve the
capture ratio per category.**

1. `PowerCalibration.finalist_sharpes_by_category: dict[str, list[float]]` — for each catalog
   category, one entry per SEARCHED symbol: the best in-sample Sharpe among that category's family
   finalists. Read off the same `Experiment.trials` the existing finalist comes from, so it costs no
   extra search. Defaulted to `{}` so every committed artifact still loads.
2. `net_capture_by_category` computed field — each category's median divided by the median net
   oracle, under the **same** ADR-055 refusal (no ratio when the net oracle sits inside Lo (2002)'s
   Sharpe standard error at the cell's own history length). Computed, not stored, for the ADR-055
   reason: a reader that re-divided could disagree with the served value and could not apply the
   refusal.
3. **This ADR does not add a "matched family" field, deliberately.** Which category matches a
   planted process is an interpretation (band reversion and AR(1) φ<0 → Mean Reversion; AR(1) φ>0 →
   Trend), and interpretations belong in the ADR and the report, not baked into an artifact that
   will outlive them. The reader picks the row; the ADR says which row and why.

## Alternatives considered

- **Redefine `capture_ratio` to use the matched family.** Rejected: it would silently change the
  meaning of a number published in four places and stored in committed artifacts, and it would bake
  the process→category map into the model (decision 3). The two numbers answer different questions —
  "how much did the search keep?" and "how much did the strategies aimed at this process keep?" —
  and both are worth having side by side.
- **Record every family's Sharpe, not the per-category best.** Rejected as 34 lists per cell for a
  question that is about kinds of strategy, not individual ones; ADR-057's names already identify
  the individual winner.
- **Report the winner's category only (no Sharpes).** Rejected: that is what ADR-057 already gives,
  and it cannot say whether the matched family lost narrowly or was nowhere near — which is exactly
  the distinction between "selection noise" and "no expression", i.e. the whole open question.
- **Do nothing; the local probe is enough.** Rejected. A probe in a session transcript is not a
  measurement the project owns; that is what ADR-053 exists to prevent.

## Consequences

- Both power workflows must be re-dispatched for the per-category record to exist. The catalog is
  unchanged, so `search_config_version` stays `3f36fda2…` and the new artifacts are directly
  comparable to the committed ones — the null calibration does **not** need re-running (nothing
  about the search or the gate changes, only what is recorded).
- The band-reversion reading gets an honest numerator for the first time. If matched-family capture
  at half-lives 1–3 is ≈ 22% while total capture is ≈ 31%, then roughly a third of the reported
  capture in those cells is a strategy fitting the level, and the "the catalog captures 31% of fast
  reversion" sentence has to go from every doc that carries it.
- The same field makes the AR(1) sweep self-checking: at φ = −0.3 the Mean Reversion row should be
  the maximum row, and at φ = +0.3 the Trend row should be. A sweep where it is not would mean the
  planted process and the category taxonomy disagree, which is worth knowing on its own.

## Reversal

Drop `finalist_sharpes_by_category` and `net_capture_by_category` from `PowerCalibration`, the
collection block in `calibrate_power`, and the per-category lines in the consolidation script. No
stored artifact is invalidated: the field is defaulted and no existing ratio is redefined.
