# ADR-107: Add the Sortino ratio to backtest metrics

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)

## Context

`BacktestMetrics` (`app/research/backtesting/metrics.py`) reports Sharpe, max drawdown, total
return, and annualized return/vol. Sharpe penalizes upside and downside volatility identically —
a strategy with large, infrequent positive spikes and small, steady losses scores the same Sharpe
as one with the reverse shape, even though only the second is the risk an investor actually wants
avoided. The catalog includes several strategies whose whole thesis is an asymmetric return
profile (breakout, trend-following, vol-targeted momentum), so a symmetric-risk metric understates
their appeal and a downside-only measure is missing from the metrics layer entirely.

The Sortino ratio (Sortino & van der Meer, 1991) is the standard fix: it divides excess return by
downside semi-deviation instead of total standard deviation, so upside variance is never charged
against the strategy. It is a **descriptive metric alongside Sharpe, not a replacement and not a
gate input** — charter §4 forbids weakening or adding to validation thresholds outside a
methodology argument with evidence, and this ADR makes no such argument. It is reported for the
same reason Sharpe already is: so a reader can see the shape of the risk, not to change who
graduates.

## Options Considered

1. **Add `sortino_ratio` to the metrics layer, threaded through the API and frontend like every
   other `BacktestMetrics` field.**
   - Pro: consistent with how every existing metric is exposed; no new pattern to learn; a reader
     comparing configs on `CompareMetricsTable` gets the downside-risk read for free.
   - Con: touches five files (backend metric, engine's implicit pass-through, API response model +
     construction site, frontend type, frontend display) for one number.
2. **Compute it only inside `ParameterStability`/`GraduationGate` as an internal diagnostic, not a
   user-facing metric.**
   - Pro: smaller diff.
   - Con: hides a genuinely interesting number from the dashboard, and mixes a descriptive risk
     metric into the gate's validation surface — exactly the ambiguity this ADR's Context section
     warns against avoiding.
3. **Do nothing; Sharpe alone is sufficient.**
   - Pro: zero cost.
   - Con: the catalog's asymmetric-return strategies (breakout, trend, vol-targeted momentum) are
     the ones this metric would differentiate most, and the project already treats "one number
     hides the shape" as worth fixing (see `benchmark_relative_drawdown`, `regime_analysis.py`).

## Decision

Add `sortino_ratio(returns: pd.Series, target: float = 0.0) -> float` to
`app/research/backtesting/metrics.py`, matching `sharpe_ratio`'s annualization convention
(`sqrt(TRADING_DAYS)` scaling, implicit 0.0 risk-free/target rate, same degenerate-series
convention of returning `0.0` rather than `+inf`). Downside semi-deviation squares only the
shortfall below `target` (returns at or above it contribute zero, not a negative penalty) and
divides by the full sample size, not just the count of shortfalls — the original Sortino & van der
Meer definition. `BacktestMetrics.sortino` is a new required field computed by `from_series`, so
every caller gets it automatically. `BacktestMetricsView` (API) and the frontend `BacktestMetrics`
type gain the matching field, and `CompareMetricsTable`/`BacktestResultView` display it next to
Sharpe. It is descriptive only: `GraduationGate`, PBO, DSR, and every existing threshold are
unchanged, and this metric is not read by any of them.

## Consequences

- Every backtest response now carries a Sortino ratio alongside Sharpe, with no new request
  parameter (target rate is implicitly 0.0, consistent with Sharpe's existing convention in this
  codebase).
- A new Hypothesis property test is added mirroring §8 invariant #2 (Sharpe finite for a
  non-constant series): Sortino must be finite whenever at least one return falls below the
  target, added to `ARCHITECTURE.md` §8 as invariant #11.
- This is purely additive to response schemas (`BacktestMetricsView`, frontend `BacktestMetrics`
  type) — no existing field changes shape, so no caller of the existing metrics breaks.
- Nothing in the gate, calibration, or pool-report layer reads this field; it carries no risk of
  changing a graduation verdict now or by accident later, since it is never passed into any of
  those functions.

## Reversal

Delete `sortino_ratio`/`downside semi-deviation` helper, the `sortino` field, its API/frontend
plumbing, and invariant #11. Nothing else depends on it.
