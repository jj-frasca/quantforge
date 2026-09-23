# ADR-108: Add the Calmar ratio to backtest metrics

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)

## Context

ADR-107 added the Sortino ratio alongside Sharpe: both are return-over-dispersion measures (total
standard deviation for Sharpe, downside semi-deviation for Sortino). Neither answers a question a
reader asks just as often about a strategy's risk: *how bad was the worst drawdown relative to what
the strategy earned?* `BacktestMetrics` already computes `max_drawdown` and `annualized_return`
independently, but a reader has to hold both numbers in their head and divide them manually to get
that answer — every other ratio in this file is precomputed for exactly that reason.

The Calmar ratio (Young, 1991) is the standard measure for this: annualized return divided by the
magnitude of maximum drawdown. It is widely reported in CTA/managed-futures performance
disclosures specifically because volatility-based ratios (Sharpe, Sortino) can look acceptable
while a strategy's drawdown history would make most investors walk away — the two questions are
genuinely different and both are already latent in this file's own fields.

Like Sortino, this is a **descriptive metric, not a gate input** — charter §4 applies unchanged,
and this ADR makes no argument for or against any validation threshold.

## Options Considered

1. **Add `calmar_ratio` to the metrics layer, following the exact ADR-107 pattern** (backend
   function + `BacktestMetrics` field + `BacktestMetricsView` + frontend schema/type +
   `BacktestResultView`/`CompareMetricsTable` display).
   - Pro: `max_drawdown` and `annualized_return` are already computed fields on the same
     dataclass — this is pure composition, not a new statistical estimate. Consistent with how
     every other metric here is surfaced, including the one just added.
   - Con: one more required field on a response schema several components already destructure.
2. **Compute it client-side in the frontend from the two existing fields, add no backend field.**
   - Pro: zero backend diff.
   - Con: splits "how a metric is defined" across two languages/repos for no reason — every other
     derived metric here (Sharpe, Sortino, IR) is computed once, in Python, and every consumer
     reads the number rather than re-deriving it. A frontend reimplementation is also the kind of
     drift ADR-010's shadow-validator lesson (`feedback-frontend-shadow-validators`) warns against.
3. **Do nothing; Sharpe and Sortino already describe risk-adjusted return.**
   - Pro: zero cost.
   - Con: neither is a drawdown-relative measure, and `max_drawdown` currently sits unreduced next
     to `annualized_return` for every reader to manually divide — precisely the gap ADR-107 closed
     for downside dispersion, left open here for drawdown.

## Decision

Add `calmar_ratio(annualized_return: float, max_drawdown: float) -> float` to
`app/research/backtesting/metrics.py`: `annualized_return / abs(max_drawdown)`, returning `0.0`
when `max_drawdown == 0.0` (a flat/never-drawn-down equity curve — mirrors `sharpe_ratio`'s and
`sortino_ratio`'s degenerate-series convention of `0.0` rather than `+inf`). Unlike Sharpe/Sortino
this takes the two already-computed scalars as arguments rather than a returns Series — there is no
new estimation, only a ratio of two existing `BacktestMetrics` fields, so the function stays pure
and trivially testable without a Series fixture. `BacktestMetrics.calmar` is a new required field
computed by `from_series`. `BacktestMetricsView` and the frontend `BacktestMetrics` type gain the
matching field; `CompareMetricsTable`/`BacktestResultView` display it next to Sharpe and Sortino.
Descriptive only: no gate, threshold, PBO, or DSR calculation reads it.

## Consequences

- Every backtest response now carries a Calmar ratio with no new request parameter — it is a pure
  function of two fields the response already returns.
- A Hypothesis property test is added mirroring §8 invariant #11 (Sortino finite when applicable):
  Calmar must be finite whenever `max_drawdown != 0.0`, recorded as §8 invariant #12.
- Purely additive to `BacktestMetricsView` and the frontend `BacktestMetrics` type — no existing
  field changes shape.
- Nothing in the gate, calibration, or pool-report layer reads this field.

## Reversal
Delete `calmar_ratio`, the `calmar` field, its API/frontend plumbing, and invariant #12. Nothing
else depends on it.
