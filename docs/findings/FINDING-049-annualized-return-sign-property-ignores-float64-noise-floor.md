# FINDING-049: Annualized-return sign property doesn't allow for the float64 noise floor

- **Severity:** Low
- **Status:** Resolved by ADR-121
- **Found:** 2026-09-23/24, autonomous session 104 (Hypothesis, during a routine `make check`)
- **Affects:** `tests/unit/test_backtest_engine.py::test_annualized_return_has_compounded_total_return_sign`

## Finding

ADR-110's `test_annualized_return_has_compounded_total_return_sign` asserts
`np.sign(metrics.annualized_return) == np.sign(metrics.total_return)` for any Hypothesis-generated
return series. The property is true in exact arithmetic: both quantities are monotone,
sign-preserving transforms of the same compounded log-growth sum
(`_compounded_log_growth(returns)`) — `total_return` exponentiates it directly, `annualized_return`
exponentiates it scaled by `TRADING_DAYS / len(returns)` first.

That scaling is exactly what breaks the property in float64. Hypothesis found
`returns=[0.0, 6.7546852396317814e-18]`: the raw log-growth sum (~6.75e-18) is far below float64's
representable epsilon (~2.22e-16) relative to 1.0, so `exp(6.75e-18)` rounds to exactly `1.0` and
`total_return` comes out as exactly `0.0`. The annualized exponent scales that same sum by
`TRADING_DAYS / 2 = 126`, landing at ~8.5e-16 — just *above* the epsilon threshold — so
`exp(8.5e-16)` rounds to a value fractionally above `1.0`, and `annualized_return` comes out as
`8.88e-16`, a positive nonzero float. `np.sign` disagrees (`0` vs `1`) even though both numbers are
financially indistinguishable from zero (any real return series has a total_return several orders
of magnitude above 1e-9).

This is a test-precision gap, not a production defect: `total_return`/`annualized_return`
(`app/research/backtesting/metrics.py`, ADR-110) are mathematically correct; IEEE 754 arithmetic
simply cannot represent sub-epsilon log-growth consistently across two different scale factors. The
test's `.hypothesis/` example cache (gitignored, machine-local) had not previously found this exact
input, so it passed on every `make check` run until this session's routine gate run.

## Reproduction

```python
import pandas as pd
from app.research.backtesting.metrics import BacktestMetrics

m = BacktestMetrics.from_series(pd.Series([0.0, 6.7546852396317814e-18], dtype="float64"))
# m.total_return == 0.0, m.annualized_return == 8.881784197001252e-16
```
