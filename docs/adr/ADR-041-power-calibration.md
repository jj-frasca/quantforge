# ADR-041: Measure the gate's power, not just its Type-I error

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-036 (null-model calibration), ADR-037 (sharded scheduled calibration)
- **Relates to**: ADR-018 (universe deflation), ADR-034 (meta-labeling declined)

## Context
As of today the gate's **Type-I error is measured**: run the unmodified search over 200 symbols
with no edge by construction and 1.0% of them graduate, of which **zero** clear the ADR-018
universe-deflation bar (ADR-036/037, runs 32286389784 / 32292934031 / 32297042398). That is a
genuinely strong result and it is half of a hypothesis test.

The other half has never been measured, and it is the half that decides how to read this project's
headline finding. `scripts/pool_report.py` reports **0 of 40 graduates clear the deflation bar**,
and every session since 2026-08-18 has treated that as a statement about the *strategies*. It is
equally consistent with a statement about the *bar*:

- If the gate has reasonable **power** — it graduates a symbol that genuinely has an edge, most of
  the time — then "0 clear the bar" means the catalog has not found an edge, and the honest
  response is to keep searching or to search differently.
- If the gate has near-zero power — it would reject a real edge too — then "0 clear the bar" means
  almost nothing about the strategies, and the effort spent widening the universe is wasted on an
  instrument that cannot register a hit.

These lead to opposite decisions, and nothing in the repository currently distinguishes them. A
test whose Type-II error is unknown cannot support the interpretation the project's central claim
rests on. It also bears directly on ADR-034, which declined meta-labeling with the precondition
"one primary graduate clears the deflation bar" — a precondition worth far less if that event is
unreachable by construction.

## Decision
**Add a power calibration: plant an edge of known, measured strength, run the unmodified search and
gate, and report the detection rate.**

### The generator
`autocorrelated_edge(n_bars, *, seed, phi, vol, drift)` produces an OHLCV frame whose close returns
follow an AR(1) process, `r_t = phi * r_{t-1} + eps_t`. One knob spans both directions of the
catalog: **`phi < 0` is mean reversion** (tradeable by the RSI / Bollinger / Connors-RSI family),
**`phi > 0` is trend persistence** (tradeable by the SMA / MACD / Donchian family). The bar geometry
is built exactly as `iid_normal_null` builds it, so the only difference from the null is the serial
dependence — which is precisely the thing every catalog strategy claims to trade.

### Measuring the effect size honestly
Rather than deriving a closed-form Sharpe for the process, each frame reports its **oracle Sharpe**:
the annualized Sharpe of the rule `position_t = sign(phi * r_{t-1})`, which is the sign of the AR(1)
conditional mean and therefore the best any causal sign-taking strategy could do on that series,
scored with the same one-bar lag the backtest engine applies. That number is measured on the same
data the search sees, so "the gate detected 40% of symbols whose oracle Sharpe was 1.2" is a
statement with no theory in it that could be wrong.

### What is reported
`PowerCalibration`: `n_symbols`, `n_detected`, **`detection_rate`**, `n_clear_deflation_bar`,
the oracle-Sharpe distribution, `phi`, and `gate_config_version`. Detection is judged in two tiers,
because they answer different questions:

1. **graduated** — passed the gate. Power of the gate as such.
2. **cleared the ADR-018 bar** — the standard the project actually holds itself to. Power against
   *this* is the number that interprets "0 of 40".

### The honest limits, stated because they bound every conclusion drawn from this
- **An AR(1) edge is stationary and always-on.** Real edges are intermittent, decay, and crowd out.
  Measured power against a planted stationary edge is therefore an **upper bound** on power against
  a real one. A low number here is damning; a high number here is not a clean bill of health.
- **The deflation bar grows with the number of symbols searched**, so power against it is only
  meaningful at a stated N, and the number reported is power against *that run's own bar*. Unlike
  ADR-037's null calibration this is deliberately **not sharded**: there, shards of one measurement
  had to be merged before the bar could be judged at the combined N; here each phi is a separate,
  self-contained measurement, so a job judges its own bar and there is nothing to merge. The
  workflow parallelizes across **phi values**, not across slices of one run.
  N = 50 per phi is well below the 607-symbol production universe, so the bar these runs face is
  correspondingly lower — state the N whenever the number is quoted.
- **This measures the gate, not the catalog.** A phi the catalog has no strategy for would measure
  as zero power and mean only that the catalog has a blind spot — which is itself worth knowing,
  and is why the phi sweep spans both signs.

### What this does NOT license
Nothing about this changes a threshold. If power turns out to be low, the response is **not** to
loosen the gate — charter §4 is explicit and this ADR does not create an exception. A low power
measurement is evidence for a different search (longer holdouts, fewer better-motivated hypotheses,
a smaller universe so the deflation bar is lower), or for stating plainly in the README that the
bar is currently unreachable. Both are honest; weakening DSR/PBO/MinTRL to manufacture a graduate
is not.

## Measured, 2026-08-19 (run 32304778979, N = 50 per phi, 3000 bars, full 34-strategy catalog)

> **SUPERSEDED FOR PRODUCTION, 2026-08-20.** This table predates whole-search DSR accounting,
> production refinement, and the enforced 200-candidate budget. Production-parity run 32341906980
> measured 0/50 detections at every phi. ADR-049 attribution found DSR passed 0/50 in every cell;
> at phi +0.30 the other components passed PBO 43/50, stability 40/50, and
> MinTRL/holdout/beat-buy-and-hold 50/50. See FINDING-006 before interpreting DSR rejection as
> absence of edge. The historical table remains reproducible evidence for its stated procedure.

| phi | direction | oracle Sharpe (median) | detection rate | clear the ADR-018 bar (of 50) |
|---|---|---|---|---|
| -0.30 | mean-reverting | +3.98 | 16% | 6 |
| -0.20 | mean-reverting | +2.60 | 6% | 2 |
| -0.10 | mean-reverting | +1.29 | **0%** | 0 |
| +0.10 | trending | +1.26 | **0%** | 0 |
| +0.20 | trending | +2.56 | 54% | 8 |
| +0.30 | trending | +3.92 | 64% | 27 |

**1. The gate is not a dead instrument.** At phi = +0.30 it detects 64% of planted edges and 27 of
50 clear the deflation bar. Detection rises monotonically with effect size in both directions. This
is the result that was actually in question, and it materially strengthens the standing "0 of 40
graduates clear the bar" finding as a statement about the *strategies* rather than about the bar.

**2. Power collapses to zero at moderate effect sizes.** At an oracle Sharpe of ~1.3 — a genuinely
excellent real-world edge — detection is **0 of 50, in both directions**. The gate has usable power
only for edges around oracle Sharpe 2.5 and above, which is far larger than anything one should
expect to find in liquid daily equities. So the honest reading of "0 of 40" is narrower than it
looked: it is strong evidence that **no edge of oracle Sharpe ≳ 2.5 exists in this catalog crossed
with this universe**, and it is nearly silent about edges around 1.0–1.5, which this pipeline cannot
see at all.

**3. The catalog is markedly better at trend than at mean reversion.** At comparable planted effect
size the asymmetry is roughly ninefold (oracle ≈ 2.6: 54% trending vs 6% mean-reverting; oracle
≈ 3.9: 64% vs 16%), even though the catalog contains more nominally mean-reversion strategies
(RSI, Bollinger, Connors RSI, Williams %R, CCI, stochastic, VWAP reversion, trend-filtered MR) than
trend ones.

**The honest alternative explanation for (3), which cannot be separated with this experiment:** the
planted process reverts at **lag 1**, while the catalog's mean-reversion strategies act on
multi-bar rolling windows (RSI-14, Bollinger-20). A trend strategy integrating over many bars
accumulates positive autocorrelation cumulatively; a 14-bar oscillator has no particular reason to
capture bar-to-bar reversion. So this may be a mismatch between the planted *horizon* and the
strategies' horizon rather than a weakness of the mean-reversion family as such. What can be said
without qualification is narrower and still useful: **the catalog cannot capture lag-1 mean
reversion.** Distinguishing the two requires an edge planted at a multi-bar horizon, which is the
obvious follow-up experiment and is not attempted here.

**What this does not license, restated because it is the tempting inference:** none of this is an
argument for loosening the gate. A test with low power and a 1% false-positive rate is a
*conservative* instrument, and conservative is what this project claims to be. The legitimate
responses are to search where large edges might plausibly live, to reduce the deflation bar
honestly by testing fewer and better-motivated hypotheses (ADR-029's quality pre-screen is exactly
this), or to state plainly that edges below oracle Sharpe ~2.5 are outside this pipeline's
resolution. Charter §4 stands.

## Alternatives considered

1. **Do nothing; power is implicit in the forward test.** The paper book does eventually reveal
   whether graduates work. Rejected on latency: ADR-033's re-evaluation trigger is 20 positions per
   cohort at ≥126 forward bars, which is months away, and it measures the graduates that exist
   rather than the ones the gate missed. Power is exactly the missed ones.
2. **Backtest a known-good published strategy on real data.** More realistic, and unusable as a
   measurement: any real series has an unknown true effect size, so a rejection cannot be
   attributed to the gate rather than to the strategy having no edge in that period.
3. **Plant the edge by injecting a signal column the strategies can see directly.** Would measure
   the plumbing, not the gate — a strategy handed its own answer detects it at 100%.
4. **Derive the theoretical Sharpe of the AR(1) trader and report power against that.** Rejected in
   favour of the measured oracle Sharpe: a derivation is one more thing that can be silently wrong,
   and the empirical version is strictly more defensible.

## Consequences
- A second calibration alongside the null, answering the question the null cannot.
- The interpretation of "0 of 40 clear the bar" becomes evidence-backed rather than assumed.
- Cost is the same shape as ADR-037's: one full-catalog search per synthetic symbol, ~7 s each on a
  cloud runner, shardable to minutes. Token-free.
- Like the null, power experiments are **never written to the research pool** — a synthetic symbol
  is not a hypothesis about a real one and must not inflate the MinTRL denominator.

## Reversal
Delete `autocorrelated_edge`, `oracle_sharpe`, `measure_power` and `PowerCalibration` from
`app/research/lab/calibration.py`, plus the driver. `calibrate_gate` and the gate itself are
untouched; nothing depends on the new code.
