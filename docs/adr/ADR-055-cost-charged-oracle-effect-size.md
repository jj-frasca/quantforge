# ADR-055: Charge the oracle the same transaction costs the catalog pays

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-041 (power calibration), ADR-042 (multi-bar reversion power), ADR-045 (capture efficiency)
- **Relates to**: ADR-043 (detectable-edge frontier), ADR-051 (measure at production parity), ADR-053 (commit the power record)

## Context

The power calibration reports two numbers side by side and invites the reader to divide one by the
other. `oracle_sharpes` is the annualized Sharpe of `position = sign(E[r_t | F_{t-1}])` — a trader
who knows the planted process exactly. `finalist_observed_sharpes` is what the catalog's best
config actually achieved. ADR-045's `capture_ratio` is their ratio, read as "how much of the planted
edge the catalog can express".

**The two are computed under different cost accounting.** `oracle_sharpe_of` multiplies the
position by the return and stops. Every catalog strategy is run through `BacktestEngine`, which
charges `cost_rate = 0.001` on turnover (`|Δposition|`) on every bar. The oracle is a *sign*
strategy, so it flips between ±1 and its turnover is large — and the planted processes are exactly
the ones that make it flip most.

Measured over ten seeds at 5,400 bars, with the same 10bp charged to the oracle's own position
series:

| planted process | gross oracle | **net oracle** | oracle turnover/bar |
|---|---|---|---|
| AR(1) φ = +0.30 | 3.99 | 2.92 | 0.81 |
| AR(1) φ = −0.30 | 3.93 | 2.41 | 1.19 |
| AR(1) φ = +0.20 | 2.63 | 1.48 | 0.87 |
| AR(1) φ = −0.20 | 2.60 | **1.15** | 1.13 |
| AR(1) φ = +0.10 | 1.25 | **0.02** | 0.93 |
| AR(1) φ = −0.10 | 1.36 | **−0.06** | 1.07 |
| band, half-life 1 | 2.66 | **1.76** | 0.67 |
| band, half-life 3 | 2.75 | 2.18 | 0.42 |
| band, half-life 20 | 1.47 | 1.25 | 0.16 |

Three things follow immediately, and all three change how already-published numbers must be read.

1. **The zero-power cells at |φ| = 0.10 contain no achievable edge at all.** Their net oracle is
   0.02 and −0.06. The project has been describing those cells as "an edge of oracle ≈ 1.3 that the
   gate did not detect". Nothing could have detected it; there was nothing left after costs. That
   is a much stronger and simpler statement than the frontier argument currently used to explain
   them, and it is not the same statement.
2. **The "matched oracle ≈ 2.6" comparison at the heart of the current capture reading is not
   matched.** AR(1) φ = −0.20 and band half-life 1 have nearly identical *gross* oracles (2.60 vs
   2.66) and opposite detection rates (22% vs 0%). Net of costs the band process is the *more*
   tradeable of the two (1.76 vs 1.15). The capture gap therefore survives the correction — it gets
   larger, not smaller — but the comparison as published rests on an equality that does not hold.
3. **Every capture ratio in the repo is understated**, because its numerator pays costs and its
   denominator does not. ADR-045 already calls the ratio a selection-biased *upper* bound; it is
   simultaneously biased downward by this, and the two biases have no reason to cancel.

## Decision

**Record the oracle's Sharpe net of the same cost model the catalog pays, alongside the gross one,
and report capture against both.** Nothing about the gate, the thresholds, the planted processes or
the search changes.

1. `DEFAULT_COST_RATE = 0.001` becomes a named constant in `backtesting/engine.py` and the default
   of `BacktestEngine.__init__`, so the oracle and the catalog cannot be charged different rates by
   drift.
2. `oracle_sharpe_of` / `oracle_sharpe` take a `cost_rate` keyword defaulting to `0.0`. The default
   preserves the existing gross definition exactly, so no committed artifact changes meaning.
3. `PowerCalibration.net_oracle_sharpes`, defaulted to `[]` so every committed artifact still loads,
   plus `net_capture_ratio` and `net_oracle_sharpe_percentiles` with the same partial-artifact
   refusals `capture_ratio` already uses.
4. Both power drivers record it, and the consolidation, the endpoint and the dashboard report the
   net ratio beside the gross one rather than replacing it.
5. Both power workflows are re-dispatched in the same change, so the committed record states the
   new number rather than leaving it derivable-but-unstated.

## Alternatives considered

- **Replace the gross oracle with the net one.** Rejected. The gross oracle is a statement about the
  *information* in the planted process, which is what a horizon sweep is about, and it is the number
  ADR-041/042's entire measured record is expressed in. Overwriting it would silently restate
  published results; recording both makes the correction auditable.
- **Give the oracle a continuously sized position (∝ the conditional mean) so it trades less.**
  Rejected here, though it is the better long-run idea. It changes the definition of effect size and
  would invalidate every oracle number ADR-041 and ADR-042 published, in a commit whose purpose is
  to make an existing comparison honest. Worth its own ADR, with its own re-measurement.
- **Lower `cost_rate` so the planted edges survive.** Rejected outright. That is tuning the
  simulation until the funnel looks better, which is the spirit of what charter §4 forbids. The cost
  model is the one the research pool is judged under; the oracle must meet it, not the reverse.
- **Charge the oracle costs and leave the reporting alone.** Rejected: the whole defect is that a
  reader divides two numbers that are not on the same scale, and that division is done in the
  dashboard, in `consolidate_power_calibration.py` and in three docs.

## Consequences

- The zero-power cells at |φ| = 0.10 become explicable without appeal to the detection frontier, and
  the frontier argument is freed to explain the cells where an achievable edge *did* exist.
- Capture ratios rise. This must not be read as the catalog improving: it is the denominator being
  corrected, and both numbers stay in the artifact so the correction is visible.
- The band-vs-AR(1) capture gap that ADR-051 identified as "the first result pointing at a concrete
  strategy-design action" is strengthened. At matched *net* oracle the band family is detected less
  often while being more tradeable, which is a sharper statement of the same finding.
- **Limitation, stated because it bounds the claim:** the oracle is a sign strategy, so its turnover
  is an artifact of that choice as much as of the process. The net oracle is therefore a *lower*
  bound on what a cost-aware trader with perfect knowledge could achieve, exactly as the gross one
  is an upper bound. The truth is bracketed, which is more than was true before, and the second
  alternative above is how the bracket gets tightened.
- Type-I error is untouched: the null calibration plants no edge and has no oracle.

## Reversal

Drop `net_oracle_sharpes` (defaulted, so artifacts written under this ADR still load), the two
properties, the `cost_rate` keywords, and the net columns in the report, the endpoint and the panel.
`DEFAULT_COST_RATE` can stay or be inlined; it changes no behaviour either way. No threshold, gate,
planted process or committed measurement is touched by any of it.
