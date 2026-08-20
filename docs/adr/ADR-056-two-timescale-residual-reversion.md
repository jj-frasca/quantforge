# ADR-056: Act on the measured capture gap — separate the level from the deviation

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-055 §Measured (net capture), ADR-045 (capture efficiency), ADR-042 (band-reversion power)
- **Relates to**: ADR-041 (power calibration), ADR-051 (measure at production parity)

## Context

Every calibration result so far has been a statement about the gate. ADR-055's measurement is the
first that is a statement about the **catalog**, and it is specific enough to act on.

Net of the transaction costs the catalog itself pays, the best in-sample config *beats* a
cost-paying sign oracle on AR(1) processes (net capture 104–126%) and reaches only **29–45% on band
reversion at half-lives 1–5**, where detection is 0/50 in every cell. Two controls rule out the easy
explanations: those fast band cells have a **higher** net oracle (+1.70) than the AR(1) cell the gate
detects 22% of the time (+1.15), so it is not that less edge is present; and net capture rises
monotonically with the reversion horizon (32% → 58% from half-life 1 to 20), which is the signature
of a *resolution* limit rather than of a missing effect.

The planted process is `log price = random-walk level + fast mean-reverting deviation`. That is not
an exotic construct — it is the standard statistical-arbitrage decomposition (Avellaneda & Lee 2010)
and a plain statement of a market behaviour: a slowly-drifting fair value with fast transient noise
around it. **The catalog has no strategy that separates the two timescales.** `mean_reversion`
z-scores price against a rolling mean and divides by the standard deviation *of the same window*;
Bollinger, Keltner, VWAP reversion and every oscillator share that structure. One window has to do
two incompatible jobs: short enough and it absorbs the transient into the "level" (destroying the
signal), long enough and its lag against a drifting level swamps the residual with level error.

## Decision

**Add one strategy that estimates the level and the deviation's scale on two independent
timescales, and measure whether it moves the band-reversion capture number.**

1. `two_timescale_reversion`: level from an exponentially weighted mean with span `level_span`;
   residual = close − level; z-score of that residual against its **own** rolling standard deviation
   over a separate, shorter `scale_window`; position `-clip(z / k, -1, 1)`. Category **Mean
   Reversion** — an existing one, so no frontend schema or guard test changes.
2. The two windows are independent grid parameters. The decision this ADR makes is *structural*
   (decouple the level estimator from the scale estimator), not numeric.
3. **The measurement protocol, which is the load-bearing half.** Adding a strategy changes the
   catalog, which per `validation-methodology.md` §7.2 invalidates the Type-I error and BOTH power
   curves. All three workflows are re-dispatched together at the same `n_bars`, and the band cells
   are read afterwards. A capture improvement claimed without a fresh Type-I error is not a result.

## Alternatives considered

- **Tune the strategy against the planted process's parameters (rho, deviation share).** Rejected,
  and this is the restraint that matters. Fitting a strategy to the calibration harness makes every
  subsequent power number in-sample to that harness and destroys the only instrument this project
  has for judging itself. The design is taken from the *stated market behaviour*, the parameters
  come from the ordinary catalog grid, and the sweep is run once afterwards.
- **Add several fast-reversion strategies at once.** Rejected: with N strategies changed the capture
  number moves for reasons that cannot be attributed, and the DSR/MinTRL denominator grows for every
  symbol in the pool. One strategy is the smallest change that can answer the question.
- **Widen the existing `mean_reversion` grid to shorter windows.** Rejected as already tested and
  negative: ADR-045 records that 2-bar configurations are searched at both horizons and win at
  neither, so the gap is not a missing short window — it is the single-window structure itself.
- **Do nothing; the gap is a fact about markets, not about us.** Rejected. The gap was measured
  against a *planted* process whose net oracle is +1.70 — an edge that is there by construction and
  that the catalog does not convert. That is a statement about the catalog.

## Consequences

- The catalog grows to 35 single-name strategies, so every symbol's lifetime trial count rises and
  the DSR/MinTRL bar rises with it. That is the ADR-046 accounting working as intended and is not a
  reason to avoid the addition — but it does mean the new strategy must *earn* its place in capture,
  and if it does not, the honest action is to record that and consider removing it.
- Type-I error and both power curves must be re-measured before any of them is quoted again.
- If capture on the fast band cells does not move, that is a real result too: it would mean the
  limit is estimation noise on the deviation rather than the catalog's structure, and it would
  point the next unit at the *estimator* (a Kalman gain fitted per symbol) rather than at more
  strategies.

## Reversal

Delete `two_timescale_reversion.py`, its config, its builder branch, its catalog entry and its
tests, then re-dispatch the three calibration workflows. Nothing else depends on it; no stored
experiment is invalidated, because a pool row records the strategy names it actually searched.
