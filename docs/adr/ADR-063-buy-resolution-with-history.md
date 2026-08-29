# ADR-063: Buy resolution with history, not with a smaller universe

- **Status**: Accepted
- **Date**: 2026-08-29
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-043 (detectable-edge frontier), ADR-015 (sealed holdout), ADR-018 (universe deflation)
- **Relates to**: ADR-051 (null history length), ADR-044 (search fingerprint), ADR-060/061 (what the
  measurements identified as the binding constraint)

## Context

The ADR-055 → ADR-061 arc ended by naming its own constraint. ADR-061 showed the catalog converts
**103–105%** of what a Kalman filter with the true process parameters could recover, so the 0/50
detection rate on the band cells follows from the frontier alone and not from anything the catalog
lacks. ADR-060 then asked the same question on real data: over 3,255 pooled experiments the median
lead of the winning strategy *category* over the runner-up is **+0.074** against a Lo (2002) Sharpe
standard error of **0.215** — the kind of strategy the search selects is inside a third of one
standard error of the kind it passed over. Neither result is a defect in the search. Both say the
same thing: **at this history length the data does not separate the hypotheses.**

`app/research/lab/frontier.py` factors that statement into its two inputs, and the pool report
prints the factorisation on every run:

> an edge must be a TRUE annualized Sharpe of 2.13 to clear that bar 80% of the time (4.3y holdout,
> SE 0.48) — halving the universe → 2.04; doubling the holdout → 1.51.

The ADR-018 bar is `E[max of N null Sharpes]`, which scales as `sqrt(2 ln N / T)`, and the power
requirement adds `z·SE(SR)` where `SE ∝ 1/sqrt(T)`. **Both terms fall as `1/sqrt(T)` in holdout
length and only as `sqrt(ln N)` in universe size.** Cutting the universe in half buys 5%; doubling
the holdout buys 29%. The project has spent six ADRs on the numerator of capture and none on `T`.

**`T` is not a fixed property of the world here. It is a constant in nine scripts.** Every driver
fetches from `START = datetime(2005, 1, 1)`, so a long-lived name carries ~5,448 bars and the
sealed holdout — the calendar-latest 20% (ADR-015) — is 4.3 years. Yahoo serves considerably more.
Measured now, on a random 70-symbol sample of the 607-name discovery universe, fetching from
1990-01-01 instead:

| percentile of the universe | p10 | p25 | **median** | p75 | p90 |
|---|---|---|---|---|---|
| bars available from 1990 | 2,488 | 5,078 | **7,444** | 9,232 | 9,232 |

52 of the 70 (74%) are listed before 2005 and are therefore *currently truncated by the constant,
not by the vendor*. The rest (recent IPOs, newer ETFs) are unaffected by this decision either way.

What that buys, from `frontier.py` at the live universe size of 607 symbols:

| history | holdout | ADR-018 bar | SE at the bar | detectable at 80% power |
|---|---|---|---|---|
| 5,448 bars (today) | 4.32y | 1.722 | 0.482 | **2.128** |
| 7,444 bars (new median) | 5.91y | 1.473 | 0.412 | **1.820** |
| 9,232 bars (p75 and above) | 7.33y | 1.323 | 0.370 | **1.634** |

## Decision

**Fetch the single-name search window from 1990-01-01, from one named constant, and re-measure the
gate at the history the hunt actually sees.**

1. `app/research/lab/history.py` holds the two windows the platform has, and nothing else:
   - `SEARCH_HISTORY_START = 1990-01-01Z` — the single-name search path (`shard_hunt`, `hunt`,
     `run_hunt`) and the calibrations that must mirror it.
   - `RECENT_HISTORY_START = 2005-01-01Z` — every path that only needs a recent tail: the paper
     book, the broker, cross-sectional forward scoring, pool consolidation's position management,
     and the cross-sectional hunt.
   The nine duplicated `START = datetime(2005, 1, 1, tzinfo=UTC)` literals are replaced by an import,
   and a test asserts no script re-introduces a bare date literal. Nine copies of a number that
   determines the project's central statistic is how it went unexamined for six ADRs.
2. **The cross-sectional hunt deliberately keeps the recent window.** Its panel is
   `panel.dropna()` over the union of dates, so the usable block is bounded by its *newest* member
   (a 2012 listing in `large_cap.txt`). Fetching each name from 1990 would add fetch cost and change
   nothing about the panel. Where the extra history cannot reach the estimator, it is not bought.
3. `CALIBRATION_N_BARS` moves into the same module at **7,400**, replacing the three independent
   `N_BARS = 5400` constants in `scripts/null_calibration.py`, `scripts/power_calibration.py` and
   `scripts/horizon_power_calibration.py`.
   ADR-051's whole point is that the null must be judged on the length the hunt sees; that
   requirement is now expressed by both constants living in one file, where a disagreement is
   visible. The value is the sampled median, and it is **fixed, not computed from today's date**,
   because a calibration artifact must be reproducible (ADR-051's rule, unchanged).
4. **Re-dispatch the null and both power calibrations at the new length before quoting either.**
   The catalog is untouched, so `search_config_version` stays `3f36fda2…` — but ADR-058's rule
   applies exactly here: *a matching fingerprint licenses reusing a measurement, not reusing a
   measurement taken at a different history length.* The committed artifacts at `n_bars=5400`
   describe a gate that no longer runs.

## Why this is not threshold-weakening (`AUTONOMY_CHARTER.md` §4)

The charter forbids weakening a validation threshold to manufacture a graduate. This ADR changes no
threshold. The ADR-018 bar and the MinTRL requirement are **derived** from `(N, T)` at judgement
time and are recomputed per symbol on every run; nothing in `GateConfig` moves, and
`gate_config_version` is unchanged. The bar falling from 1.72 to 1.47 is not a decision — it is what
`E[max of 607 null Sharpes]` *is* over 5.9 years instead of 4.3. The estimate's standard error falls
with it, by construction, at the same rate. A longer holdout makes graduation more likely only in
the sense that more evidence makes any true statement more provable, which is the only mechanism
this project is willing to use. The bar rises again, automatically, the moment the universe grows.

## Alternatives considered

- **Raise `holdout_fraction` from 0.2 to ~0.34.** Reaches the same holdout length out of the
  existing 2005+ data and needs no new bars. Rejected: it *converts* search history into holdout
  rather than adding information, leaving 14 years to search over — and it would silently redefine
  the split for every experiment already in the pool. Fetching more bars is strictly more
  information; re-slicing is a transfer.
- **Halve the universe** (the other term in the frontier). Rejected on the arithmetic above: 5%
  against 14–23%, and it throws away the breadth that makes "nothing graduated" a claim worth
  making.
- **Fetch from 1962 / `period=max`.** Yahoo serves it for a minority of names. Rejected: the
  marginal `1/sqrt(T)` gain is small, it is available for too few symbols to move the median, and
  pre-1990 daily data sits before the 1987 structural break and well before decimalization —
  the regime-relevance objection below gets much harder to answer. 1990 keeps three complete bear
  markets (2000, 2008, 2020) inside the searched window.
- **Do nothing and add strategies.** ADR-056/058 already ran that experiment and reversed it.

## Consequences

- **Survivorship bias grows, and it is mostly cancelled by the gate's own design.** The discovery
  universe is *today's* S&P 500 plus ETFs, so extending backwards studies names that survived 36
  years rather than 21. The graduation test is a *relative* one — a strategy must beat
  buy-and-hold **on the same symbol** over the same holdout (ADR-016) — so a survivor's drift sits
  on both sides of that comparison. What does not cancel is the in-sample search: it now optimizes
  over a longer stretch of a known survivor's life. This is a real cost and it is why the decision
  is justified by holdout length, which the bias does not touch, rather than by in-sample results.
- **Costs are anachronistic on the oldest bars.** The backtester charges a flat rate; 1990s spreads
  were wider (eighths until 2001). The search may therefore prefer configs that traded a market that
  no longer exists. The sealed holdout is entirely post-2019 and decides graduation, so this
  degrades *selection quality*, not the honesty of the verdict — and it is measurable: if the pool's
  holdout Sharpe distribution shifts down after this change, the extra in-sample history is hurting
  and the split, not the fetch, should be revisited.
- **Existing pool rows carry the old length.** Bars and MinTRL are computed per experiment from that
  experiment's own history, so mixed-length rows stay individually valid; ADR-052 already records
  the search family and ADR-051's `n_bars` comparison is per-artifact. The pool report's median
  history will drift from 5,444 to ~7,400 as symbols are re-searched.
- **Runtime grows ~35% on the daily discovery matrix** (a shard is ~9 min today) and proportionally
  on the monthly calibrations. Free minutes on a public repo; no cost limit is approached.
- **Data quality on the oldest bars is now load-bearing.** The DataQualityEngine already runs on
  every fetched frame and flags what it finds; the extended window is exactly where a bad
  split-adjustment would show up first.

## How to reverse

Set `SEARCH_HISTORY_START` back to `2005-01-01` and `CALIBRATION_N_BARS` back to `5400`. The
committed `n_bars=5400` calibration artifacts then apply again unchanged, and the pool self-heals as
symbols are re-searched. No stored artifact is invalidated by either direction — each records the
length it was measured at.

## What would show this was wrong

The re-dispatched power calibration is the test, and the criterion is stated before the measurement:
**detection at the cells that currently sit at 0% must rise, or the median holdout Sharpe of the
pool must not fall.** Concretely, the AR(1) φ = ±0.1 cells (0/50 today) and the band half-life 3–5
cells (0/50 today) sit against an achievable oracle of +0.51 to +0.95 (ADR-061) and a requirement
that falls from 2.13 to 1.82 — if none of them moves off zero at the longer holdout, then holdout
length is not the binding constraint either, and the honest conclusion is that this universe carries
no edge of a size any amount of daily history can resolve.
