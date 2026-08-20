# ADR-045: Record capture efficiency, and correct ADR-042's prescription

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-041 (power calibration), ADR-042 (horizon sweep), ADR-043 (detectable frontier)
- **Note on numbering**: ADR-044 is taken by a concurrent peer session's PR #10.

## Context
ADR-043 defined the factorization but could not complete it. Measured power (ADR-041/042) is

```
power = f(statistical resolution, capture efficiency)
```

where **resolution** is the frontier ADR-043 computes — the true Sharpe an edge must have for the
ADR-018 bar to be cleared 80% of the time, assuming a strategy converts the edge perfectly — and
**capture efficiency** is the fraction of an available edge the catalog actually converts. The
frontier is computed; capture has never been measured, so the factorization has one known term and
two unknowns.

It is measurable almost for free. A power run already searches every planted symbol with the full
catalog and already measures each symbol's oracle Sharpe; the ratio of the best searched
configuration's Sharpe to the oracle's is capture efficiency, and it is being discarded.

There is also something to correct. ADR-042 concluded, in reading #4, that the catalog's blind spot
at a 1-bar reversion half-life is that "a one-bar effect is invisible to every 14-to-20-bar
oscillator in the catalog [...] the fix, if this is ever worth fixing, is a short-window strategy".
That was a plausible mechanism stated without checking, and it is **wrong on the facts**:
`grid_from_catalog` resolves `window = 2` as the first coarse grid point for `rsi_mean_reversion`,
`connors_rsi`, `bollinger_bands` and `mean_reversion` — the searched grid already contains 2-bar
configurations, and `connors_rsi` defaults to a 2-bar window by design.

## Decision
**1. `PowerCalibration` records the finalist in-sample Sharpe of every searched symbol, and exposes
`capture_ratio` = median finalist Sharpe / median oracle Sharpe.**

One entry per SEARCHED symbol, not per detection: conditioning on detection would select the
symbols where capture happened to be high and report an inflated number. The finalist is the same
max-DSR trial the gate judges, so the ratio describes the configuration the pipeline would actually
have used.

**2. The ratio is an upper bound, and is labelled as one.** The finalist's `observed_sharpe` is
in-sample and chosen as the best of a grid, so it carries the selection premium the deflated Sharpe
exists to remove. Real capture on the holdout is lower. The bound is still informative, because a
*low* upper bound is conclusive: if the catalog cannot convert an edge even with selection working
in its favour, it cannot convert it at all.

**3. ADR-042's reading #4 is corrected in that ADR**, with the measurement below in its place.

### Measured, 2026-08-20 (local, 3 seeds per horizon, full coarse grid over the four principal
mean-reversion strategies, 3000 bars)

| planted half-life | oracle Sharpe | best in-sample Sharpe | capture | winning window |
|---|---|---|---|---|
| 1 bar | +2.63 / +2.80 / +3.27 | +0.73 / +0.50 / +0.96 | **0.18–0.29** | 51–100 bars |
| 5 bars | +2.20 / +2.80 / +2.83 | +1.11 / +1.25 / +1.29 | **0.45–0.50** | 26–51 bars |

**The 2-bar configurations are searched at both horizons and win at neither.** So the fast-reversion
blind spot is not a missing short-window strategy, and adding one would not fix it. The mechanism is
the generator's own arithmetic, which ADR-042 states but did not follow through: holding the
tradeable (oracle) Sharpe fixed while shortening the half-life forces the band's *amplitude* down —
the deviation's stationary standard deviation is 0.49% of price at a 1-bar half-life against 1.9% at
5 bars. A fast band worth the same per bar is a **smaller, noisier target to infer from prices**, so
what degrades is estimation, not window length. That is a property of fast mean reversion itself,
not a fixable gap in the catalog.

### What the two numbers say together
Capture ≈ 0.47 at a horizon the catalog can see, against ADR-043's requirement of a true annualized
Sharpe of 2.13 at the current design, implies this pipeline needs an underlying edge of **oracle
Sharpe ≈ 4.5** before it is likely to find anything — and 0.47 is an upper bound, so the true
requirement is worse. That is consistent with ADR-041's measured curve (64% detection at oracle
3.9, 0% at 1.3) and it is the single most useful sentence about the programme's current design.

## Alternatives considered
1. **Report capture only for detected symbols.** Simpler and biased upward by exactly the selection
   the number exists to describe.
2. **Measure capture on the holdout rather than in-sample.** Strictly better and not free: the
   holdout Sharpe is recorded only on `Graduate`, so non-graduates would need the finalist scored
   on the sealed segment and surfaced. Worth doing if capture ever becomes a published headline
   rather than a diagnostic; the in-sample bound already carries the conclusion.
3. **A standalone capture script instead of a field on the power calibration.** Rejected: it would
   re-run the same expensive search to compute a ratio from numbers the power run already has, and
   it would drift out of sync with the process actually being planted.

## Consequences
- Every future power run reports capture at no extra compute, so the ADR-043 factorization is
  complete from then on.
- One nullable-by-default list and one derived property on `PowerCalibration`; existing artifacts
  parse unchanged.

## Reversing this
Drop `finalist_observed_sharpes` and `capture_ratio`, and the driver lines that print them.
