"""Portable reproduction of Linux log1p underflow flags on valid returns."""

from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest

from app.research.backtesting import metrics


def _signal_underflow_before_log(monkeypatch):
    original = np.log1p
    calls = []

    def flagged_log(values):
        calls.append(values.copy())
        # An actual IEEE underflow obeys the active NumPy policy on every platform.
        np.multiply(np.finfo(float).tiny, np.finfo(float).tiny)
        return original(values)

    monkeypatch.setattr(np, "log1p", flagged_log)
    return calls


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("values", [[5e-324], [-5e-324], [-1e-320, 2e-320]])
def test_valid_subnormal_log_retains_decimal_output_and_caller_state(monkeypatch, dtype, values):
    calls = _signal_underflow_before_log(monkeypatch)
    returns = pd.Series(values, dtype=dtype)
    with localcontext() as context:
        context.prec = 800
        expected = np.array([float((Decimal(1) + Decimal.from_float(x)).ln()) for x in values])
    with np.errstate(all="raise"):
        original_state = np.geterr()
        actual = metrics._validated_log_returns(returns)
        assert np.geterr() == original_state
    assert len(calls) == 1
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize(
    "consumer",
    [metrics.total_return, metrics.annualized_return, metrics.BacktestMetrics.from_series],
)
def test_compounded_metrics_accept_valid_subnormal_platform_signal(monkeypatch, consumer):
    calls = _signal_underflow_before_log(monkeypatch)
    returns = pd.Series([0.0, 5e-324])
    with np.errstate(all="raise"):
        original_state = np.geterr()
        result = consumer(returns)
        assert np.geterr() == original_state
    assert calls
    if isinstance(result, metrics.BacktestMetrics):
        assert result.annualized_vol > 0
        assert result.total_return == result.annualized_return == 0
    else:
        assert result == 0


@pytest.mark.parametrize("values", [[np.nan], [np.inf], [-1.0], [-1.1]])
def test_invalid_wealth_source_is_rejected_before_platform_ufunc(monkeypatch, values):
    calls = _signal_underflow_before_log(monkeypatch)
    with np.errstate(all="raise"), pytest.raises(ValueError):
        metrics._validated_log_returns(pd.Series(values))
    assert not calls
