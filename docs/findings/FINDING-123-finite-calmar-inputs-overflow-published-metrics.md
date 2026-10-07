# FINDING-123: Finite Calmar inputs overflow published metrics

- **Date:** 2026-10-07
- **Severity:** Medium — composed backtest metrics publish a nonfinite scalar
- **Status:** Resolved — ADR-188

## Evidence

calmar_ratio(1e308,1e-308) returns infinity from two finite scalar inputs. Python float division
also does this under strict NumPy error settings. BacktestMetrics.from_series([-1e-8,270.0])
publishes infinite Calmar while all its other numeric fields remain finite: annualized return
3.5820372924887753e306, drawdown -1.0000000050247593e-8, Sharpe 11.224972159490346,
total return 269.99999729000007, annualized volatility 3030.7424833991427 and Sortino
303074248317.46423. This is an extreme but valid complete positive-wealth sample.
Research expert independently reproduced both examples.

## Correction and limits

ADR-188 refuses a nonfinite native quotient with ValueError rather than publishing or capping it.
Direct positive/negative overflow and composed-metric tests failed before correction. Independent
rational finite-ratio oracles preserve the absolute denominator and valid zero-drawdown convention. This is finite-output validation, not a
return/drawdown bound, modified estimator or graduation threshold. Do not modify generated data.
