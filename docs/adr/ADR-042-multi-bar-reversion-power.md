# ADR-042: Separate the horizon from the family — plant mean reversion at a stated half-life

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-041 (power calibration)
- **Relates to**: ADR-036/037 (null calibration), ADR-018 (universe deflation)

## Context
ADR-041 measured the gate's power against a planted AR(1) edge and found a large asymmetry: at a
comparable planted effect size the catalog detects **54% of trending edges and 6% of mean-reverting
ones** (oracle Sharpe ≈ 2.6), and 64% vs 16% at oracle ≈ 3.9. ADR-041 recorded the finding and,
deliberately, also recorded the alternative explanation it could not separate:

> The planted process reverts at **lag 1**, while the catalog's mean-reversion strategies act on
> multi-bar rolling windows (RSI-14, Bollinger-20). [...] So this may be a mismatch between the
> planted *horizon* and the strategies' horizon rather than a weakness of the mean-reversion family
> as such.

The two readings lead to different work. If it is a horizon mismatch, the catalog is fine and the
lag-1 experiment simply asked it the wrong question. If it is not, the mean-reversion half of a
34-strategy catalog — RSI, Bollinger, Connors RSI, Williams %R, CCI, stochastic, VWAP reversion,
trend-filtered MR — cannot register the effect it is named for, at any horizon, and the honest
consequence is that half the catalog is decoration.

Nothing in the repo distinguishes them, and ADR-041 named the experiment that would: plant the edge
at a **multi-bar horizon** and re-measure.

## Decision
**Add a second planted process whose reversion horizon is an explicit parameter, and sweep the
horizon at a held-constant effect size.**

### The generator
`mean_reverting_edge(n_bars, *, seed, half_life, deviation_share, total_vol, drift)` builds a log
price as a random-walk **level** plus a stationary AR(1) **deviation**:

```
dev_t   = rho * dev_{t-1} + eps_d,     rho = 0.5 ** (1 / half_life)
level_t = level_{t-1} + drift + eps_l
log P_t = log P_0 + level_t + dev_t
```

`half_life` is the number of bars in which a deviation from the level decays by half — i.e. exactly
the horizon a band/oscillator strategy is supposed to trade. `half_life = 1` (rho = 0.5) is
approximately ADR-041's lag-1 process; `half_life = 20` is a deviation that takes a month to
unwind. This is the standard band-reversion model (an Ornstein–Uhlenbeck deviation around a
stochastic trend), and it is a genuinely different process from AR(1)-on-returns, not a
reparameterization: AR(1) on returns has no level to revert *to*.

### Why `deviation_share`, not a raw deviation volatility
The generator is parameterized by the **share of total return variance contributed by the deviation
process**, with the level volatility solved for so that total return volatility stays at
`total_vol` regardless of horizon:

```
dev_vol   = total_vol * sqrt(share / (2 * (1 - rho)))
level_vol = total_vol * sqrt(1 - share)
```

Without this, changing the horizon silently changes the series' volatility and the planted effect
size at the same time, and the resulting detection numbers confound all three. Holding realized
volatility fixed across the sweep is what makes the rows comparable.

### The effect size is bounded above by the horizon — state it before measuring
The predictable part of a bar's return is `m_t = drift + (rho - 1) * dev_{t-1}`, so the fraction of
the deviation process's own variance that is predictable one bar ahead is `(1 - rho) / 2`. A
sign-taking oracle therefore cannot exceed

```
oracle Sharpe <= sqrt(252) * sqrt(2/pi) * sqrt(share * (1 - rho) / 2)   (share <= 1)
```

which for `total_vol = 1.2%/day` is roughly **6.3 at half_life 1, 3.2 at 5, 2.3 at 10, and 1.7 at
20** — and those maxima require the price to be *nothing but* the reverting deviation. This is a
consequence of the model, not of the catalog, and it matters for reading the results: at a
half-life of 10+ bars the planted edge simply **cannot** reach the oracle Sharpe ≈ 2.5 that ADR-041
found the gate needs. The sweep is therefore run in two tiers and read separately:

- **Tier A — matched effect size (oracle ≈ 2.6), `half_life` 1, 2, 3, 5.** The clean horizon test:
  the only thing that changes across these rows is how long the deviation takes to unwind. If
  detection climbs with the horizon, ADR-041's asymmetry was a horizon mismatch.
- **Tier B — the ceiling, `half_life` 10 and 20 at `deviation_share = 0.75`.** Effect size is
  bounded here by the model, so a low detection rate is expected and is **not** evidence about the
  catalog. These rows are reported to make the ceiling itself visible, because "slow band reversion
  cannot produce a large Sharpe at equity volatility" is a result about what this pipeline could
  ever find, not about what it failed to find.

Effect size is, as in ADR-041, **measured and not derived**: `oracle_sharpe_of(frame,
conditional_mean)` scores `position_t = sign(E[r_t | F_{t-1}])` on the frame the search actually
sees, with the same one-bar lag the backtest engine applies. The bound above is stated to design
the experiment; the number reported in every row is the measured one, and the two disagreeing would
itself be a finding.

### Reusing the measurement path
`measure_power` gains an `oracle_sharpes` argument so a caller that plants a non-AR(1) process can
supply the per-symbol effect size it measured, instead of `phi`. Everything else — the unmodified
search, the two detection tiers, the ADR-018 bar judged at the run's own N, the refusal to write
anything to the research pool — is shared with ADR-041 exactly as is. `PowerCalibration` records
which process was planted (`edge`, `half_life`, `deviation_share`) so an artifact is reproducible
without its workflow file.

### What this does NOT license
Unchanged from ADR-041 and restated because this experiment makes the temptation sharper: if the
catalog turns out to detect nothing at any horizon, **the response is not to loosen the gate**
(charter §4). It is to fix or retire the strategies that cannot register the effect they are named
for, or to state plainly which effects are outside this pipeline's resolution.

## Measured, 2026-08-20 (run 32327295232, N = 50 per half-life, 3000 bars, full 34-strategy catalog)

> **SUPERSEDED FOR PRODUCTION, 2026-08-20.** This table predates ADR-046/047/048. Production-parity
> run 32341908789 measured 0/50 detections at every half-life, and ADR-049 attribution measured DSR
> pass count 0/50 in every cell. Other components did pass—for example, at five bars PBO passed
> 38/50, stability 38/50, MinTRL 20/50, holdout 48/50, and beat-buy-and-hold 33/50—so DSR alone is
> sufficient to explain the composite zero. FINDING-006 records the signal-contaminated dispersion
> estimator; the historical horizon comparison below remains evidence for its stated procedure.

| tier | half-life | deviation share | oracle Sharpe (median) | detection rate | clear the ADR-018 bar (of 50) |
|---|---|---|---|---|---|
| A | 1 bar | 0.169 | +2.76 | **0%** | 0 |
| A | 2 bars | 0.288 | +2.68 | 2% | 0 |
| A | 3 bars | 0.409 | +2.73 | 6% | 0 |
| A | 5 bars | 0.651 | +2.73 | **42%** | 4 |
| B | 10 bars | 0.75 | +2.05 | 14% | 1 |
| B | 20 bars | 0.75 | +1.50 | 2% | 0 |

**1. ADR-041's asymmetry was the horizon, not the family.** Across tier A the measured oracle
Sharpe is essentially constant (+2.68 to +2.76) and realized volatility is 1.2%/day by
construction, so the *only* thing varying is how long a deviation takes to unwind — and detection
goes from **0% at a 1-bar half-life to 42% at a 5-bar one**. The catalog's mean-reversion family
can register mean reversion; it cannot register it at lag 1, which is the only horizon ADR-041 ever
planted. The reading "half the catalog is decoration" is **not supported** and should not be
repeated.

**2. The residual family gap is small.** At comparable effect size the trending number from ADR-041
was 54% (oracle +2.56) against 42% here (oracle +2.73). That is a real but modest difference —
nothing like the ninefold gap ADR-041 measured — and it is what one would expect from a catalog
whose trend strategies integrate over many bars while its oscillators need the deviation to persist
long enough to be seen and short enough to revert inside the window.

**3. Tier B behaves as its ceiling predicts, and is not evidence of a slow-horizon blind spot.**
Half-life 10 could only be planted at oracle +2.05 and detected 14%; half-life 20 at +1.50 detected
2%. Both sit on ADR-041's *effect-size* curve (0% at oracle 1.3, ~50% at 2.6), so the fall-off
across tier B is explained by the effect size the model can reach at those horizons, not by an
additional weakness at long horizons. The interesting consequence is the ceiling itself: **slow
band reversion cannot produce a large tradeable Sharpe at equity volatility**, so an edge of that
shape is outside this pipeline's resolution no matter which strategy is pointed at it.

**4. What this changes about where to search.** The catalog's blind spot is *fast* reversion, not
reversion. Nothing here licenses touching a threshold (charter §4).

> **CORRECTED 2026-08-20 (ADR-045).** This reading originally continued: "a one-bar effect is
> invisible to every 14-to-20-bar oscillator in the catalog [...] the fix, if this is ever worth
> fixing, is a short-window strategy". That mechanism was asserted without checking and is wrong.
> `grid_from_catalog` resolves `window = 2` as the FIRST coarse grid point for
> `rsi_mean_reversion`, `connors_rsi`, `bollinger_bands` and `mean_reversion`, and `connors_rsi`
> defaults to a 2-bar window by design — the short-window configurations are searched at both
> horizons and win at neither (the winning window is 26-100 bars in both cases). The real mechanism
> is this ADR's own arithmetic: holding the oracle Sharpe fixed while shortening the half-life
> forces the deviation's amplitude from 1.9% of price at 5 bars down to **0.49% at 1 bar**, so a
> fast band worth the same per bar is a smaller, noisier target to infer from prices. What degrades
> is estimation, not window length, and **a short-window strategy would not fix it.** Measured
> capture: 0.18-0.29 at a 1-bar half-life against 0.45-0.50 at 5 bars (ADR-045).

**Honest limits.** N = 50 per row, so a 42% rate carries a 95% interval of roughly 28-58% and the
0%/2% rows roughly 0-7%; the tier-A trend across four rows is far larger than that noise, but no
single row should be quoted to two digits. The planted process is stationary and always-on, so
these remain **upper bounds** on power against real, intermittent edges, exactly as in ADR-041.

## Alternatives considered
1. **Re-run ADR-041's AR(1) at a high phi to get a long horizon.** AR(1)-on-returns with phi = 0.9
   is persistent over ~7 bars, so it *is* multi-bar — but it is multi-bar *trend*, and its variance
   scales as `1/(1 - phi^2)`, so horizon and both effect size and volatility move together. It also
   cannot express reversion to a level at all, which is the thing the oscillator family claims.
2. **Change `autocorrelated_edge` to normalize its variance and reuse it.** Rejected: ADR-041's
   published table was measured with that generator, and silently changing its variance would make
   those numbers unreproducible. A new process gets a new function.
3. **Test the strategies directly rather than through the gate** — e.g. assert that Bollinger's
   backtest Sharpe rises with the planted half-life. Cheaper and answers a different question. The
   claim under test is about the *pipeline's* power, which includes parameter search, DSR/PBO/MinTRL
   and the holdout; a strategy-level assertion cannot speak to it, and ADR-041's numbers are gate
   numbers, so a comparison must be too.
4. **Sweep the strategies' own window lengths instead of the planted horizon.** The search already
   sweeps them (`n_per_param`), so this is largely already in the measurement; and it would answer
   "is the grid wide enough" rather than "is the family able to see this effect at all".

## Consequences
- One more manual-dispatch workflow (`horizon-power-calibration.yml`), matrix over half-life,
  artifacts + Slack, no commit — same shape and same reasoning as ADR-041's.
- `measure_power` acquires one optional argument and `PowerCalibration` three nullable descriptor
  fields. Existing ADR-041 artifacts and callers are unaffected (`phi` stays, `edge` defaults to
  `ar1`).
- A negative result (no detection at any horizon) would be a strong, publishable statement about
  the catalog and would make retiring or reworking the mean-reversion family the obvious next work.

## Reversing this
Delete `mean_reverting_edge`, `oracle_sharpe_of`, the workflow and the driver; drop the
`oracle_sharpes` argument and the three descriptor fields. ADR-041's power path is untouched by all
of it.


## Superseded for production by ADR-051 (2026-08-20)

This ADR's headline — "the ADR-041 asymmetry was the horizon, not the family" — was measured under
the pre-ADR-046/047/048 accounting at 3000 bars. Re-run at production parity (ADR-050 dispersion,
enforced candidate budget, production refinement) and at the hunt's own 5400-bar history, band
reversion is detected **0% at every half-life** at oracle ≈ 2.6 with DSR passing 0/50 in every cell,
while AR(1) reversion at the same oracle is detected 22% with DSR passing 39/50. The horizon does
not rescue it, and the family difference does not disappear.

The design in this ADR stands and is what makes the newer comparison legitimate: constant realized
volatility across horizons, effect size measured rather than derived, and the two-tier reading
against the deviation-share ceiling. Only the conclusion is superseded. The current numbers and the
capture-based explanation are in ADR-051 §Measured (power at the hunt's history is NOT zero).
