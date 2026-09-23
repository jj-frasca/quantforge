# FINDING-039: Backtest return ratios ignore compounded wealth

- **Severity:** High
- **Status:** Resolved by ADR-110
- **Found:** 2026-09-23, Codex autonomous session 8
- **Affects:** Backtest total return, annualized return, Calmar ratio, API, and dashboard

## Finding

`BacktestMetrics.from_series` annualizes the arithmetic mean of daily net returns with
`mean * 252`, while ADR-108 presents Calmar as annual return divided by maximum drawdown. That
numerator is not an annualized wealth return: volatility drag can make compounded wealth fall even
when the arithmetic mean is positive. Calmar consequently inherits the wrong sign and magnitude.

A deterministic 252-period path alternating `+20%` and `-18%` ends at 13.1% of its starting
wealth (a true compounded return of `-86.9%`) but reports `total_return = -89.1%`,
`annualized_return = +252.0%`, and `calmar = +2.83`. The dashboard therefore describes a deeply
losing path as earning a strongly positive annual return per unit of drawdown.

The existing `total_return(equity)` calculation has a second instance of the same accounting
problem: it divides the last equity value by the first *post-return* equity value. The engine
charges initial-position turnover on that first bar, so this denominator drops the first net
return. A flat-price strategy entering long at a 10% cost ends with 90% of initial capital but
reports zero total return. The same omitted baseline makes maximum drawdown read `0.0` instead of
`-0.10`, so the newly exposed Calmar ratio also loses its denominator on an initial loss.

Return, annualized return, and Calmar are descriptive rather than gate inputs, but contradictory
wealth accounting is still methodology evidence presented to users. A point estimate that can
reverse the sign of the realized path is not an acceptable descriptive approximation.

## Required correction

Derive total return from the complete compounded net-return path, including the first period.
Derive annualized return as the geometric compound rate over the same observations, and use that
value as Calmar's numerator. Measure drawdown against an explicit pre-return unit-wealth baseline
so the first observation cannot disappear from its denominator either. Fail closed when the path
cannot define positive finite compounded wealth. Add a fixed volatility-drag regression, an
initial-turnover-cost regression, and a Hypothesis invariant that total and annualized returns have
the same sign. Do not change a validation threshold, gate, calibration workflow, or generated data.
