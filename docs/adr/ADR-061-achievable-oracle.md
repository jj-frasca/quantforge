# ADR-061: Measure capture against what is recoverable from prices, not against the latent state

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-045 (capture efficiency), ADR-055 (net oracle), ADR-042 (band-reversion horizons)
- **Supersedes the reading of**: the "band gap" as a catalog deficiency (ADR-042 §asymmetry, ADR-045, ADR-055 rule 3, ADR-056, ADR-058, ADR-059)

## Context

The band-reversion oracle is `sign(E[r_t | F_{t-1}])` where the conditional mean is computed from
the **latent deviation** `d_t` — the process's hidden state. `mean_reverting_edge` plants
`log price = random-walk level + AR(1) deviation`; only the SUM is observable. No causal strategy,
in this catalog or any other, can see `d_t`. ADR-055 charged that oracle the catalog's transaction
costs, which was a real correction, but it left the deeper one untouched: the oracle also has
information no price-based strategy can have.

Measured directly. A Kalman filter that knows the process parameters exactly (`rho`, level vol,
deviation vol) and computes the MMSE estimate of `d_t` from observed log prices is, by construction,
the best any causal price-based strategy can do on this process. Ten seeds × 5400 bars, both oracles
scored with the same one-bar lag and the same 10bp turnover cost:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| latent-state oracle, net (ADR-055) | +1.76 | +1.99 | +2.18 | +2.29 | +1.75 | +1.25 |
| **achievable (Kalman) oracle, net** | **−0.07** | **+0.23** | **+0.53** | **+0.94** | **+0.98** | **+0.74** |
| achievable ÷ latent | −4% | 12% | 24% | 41% | 56% | 59% |
| corr(filtered, true deviation) | 0.27 | 0.33 | 0.39 | 0.52 | 0.59 | 0.58 |

**At half-life 1 there is nothing to find.** The optimal filter, given perfect knowledge of the
process, nets −0.07 Sharpe. The +1.76 that has been quoted as the available edge requires seeing the
hidden state.

Two validations were run before anything was built on this. With `deviation_share = 0.99` (the
deviation dominating), the filter recovers the state at correlation 0.91 and beats a tuned
EWM-residual estimator (0.76), so it is doing real work. At the production shares the Kalman and the
naive EWM residual correlate with the truth **equally** (0.270 vs 0.271 at half-life 1) — the
binding constraint is the estimation problem itself, not the sophistication of the estimator.

That second observation retires both of the follow-ups ADR-056 named. Its own design ("estimate the
level with a slow filter, trade the fast residual") is the naive estimator, and ADR-056
§Consequences proposed "a per-symbol Kalman gain" as the next unit if the strategy failed. Both are
now measured: neither can help, because the optimal filter is barely better than the naive one and
both are far below what the ADR-043 frontier requires.

**So the standing "band gap" finding was an artifact of the benchmark.** Reading the catalog's
measured matched-family capture against the achievable oracle instead of the latent one:
half-life 3 ≈ 119%, half-life 5 ≈ 107%, half-life 10 ≈ 100%, half-life 20 ≈ 98%, and half-life 1
refused (achievable oracle indistinguishable from zero). The catalog converts approximately
**everything a price-based strategy can convert** at every horizon where anything is convertible.
The zero detection rate is then fully explained by ADR-043's frontier: an achievable net Sharpe of
≤ 1.0 is far below the ≈ 2.1 the deflation bar requires.

## Decision

**Record an achievable oracle beside the latent-state one on every band-reversion power cell, and
read capture against it.**

1. `filtered_deviation(log_prices, rho, level_vol, deviation_vol, drift)` in `calibration.py` — the
   two-state Kalman recursion above, pure numpy, no new dependency.
2. `PlantedEdge.achievable_conditional_mean` — `drift + (rho − 1) · d̂_t`, indexed by the bar it
   predicts, exactly like the existing `conditional_mean`. Computed inside `mean_reverting_edge`,
   which already knows every parameter.
3. `PowerCalibration.achievable_oracle_sharpes` (defaulted, so no committed artifact changes
   meaning) and a served `achievable_capture_ratio` under the SAME ADR-055 refusal — a cell whose
   achievable oracle sits inside Lo (2002)'s Sharpe standard error reports no ratio, which is what
   half-life 1 must do.
4. **The AR(1) sweep deliberately gets none of this.** Its state is the observed return, so its
   latent-state oracle is already achievable — which is exactly why its capture exceeds 100% while
   the band cells' does not. Adding a redundant column there would suggest a correction was needed.

## Alternatives considered

- **Replace the latent oracle outright.** Rejected: every published ADR-041/042/045/055 number is
  taken against it, and a silently redefined denominator is the failure this whole arc has been
  repairing. Three oracles now sit side by side — gross, net, achievable — each stating what it
  assumes.
- **Estimate the filter's parameters from the data instead of passing the true ones.** Rejected for
  the benchmark: the point is an upper bound on what is recoverable. A fitted filter would measure
  estimation error on top of it and could not distinguish "not recoverable" from "not estimated
  well". Worth its own experiment later, as a *lower* bound.
- **Treat the local probe as sufficient and just correct the docs.** Rejected — ADR-053 exists
  precisely because a number that lives only in prose gets requoted after it stops being true.
- **Conclude the planted process is unrealistic and drop the band sweep.** Rejected. The sweep is
  what produced this result; a process whose edge is provably unrecoverable at fast half-lives is a
  useful control, provided it is labelled as one.

## Consequences

- The band cells stop being evidence about the catalog and become evidence about the **process**:
  its edge is mostly unrecoverable from prices, entirely so at half-life 1.
- Every doc asserting the catalog "cannot express fast reversion to a slow-moving level" has to be
  corrected. That sentence has driven a strategy addition (ADR-056) and its removal (ADR-058); it is
  the single most load-bearing wrong sentence in the repo.
- The horizon power workflow must be re-dispatched for the new column to exist. The catalog and gate
  are untouched, so `search_config_version` stays `3f36fda2…` and the null needs no re-run.
- ADR-045's capture ratio keeps its meaning and its published values. What changes is which
  denominator a *reader* should use for a process whose state is latent.

## Reversal

Drop `filtered_deviation`, the `achievable_conditional_mean` field, the two `PowerCalibration`
fields and the driver line that passes them, and restore the superseded sentence — though the
measurement in §Context would still stand, which is the point of writing it down here.
