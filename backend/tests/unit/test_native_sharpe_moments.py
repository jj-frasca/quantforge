"""Native measurability and exact constant policy for foundation return metrics."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from app.research.backtesting.metrics import (
    BacktestMetrics,
    return_moments,
    sharpe_confidence_interval,
    sharpe_ratio,
)


def _decimal_sample_sharpe(values) -> float:
    with localcontext() as context:
        context.prec = 90
        observations = [Decimal.from_float(float(value)) for value in values]
        mean = sum(observations) / len(observations)
        variance = sum((value - mean) ** 2 for value in observations) / (len(observations) - 1)
        return float(Decimal(252).sqrt() * mean / variance.sqrt())


@pytest.mark.parametrize("scale", [1e200, 1e-200])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("interval", [False, True])
def test_nonconstant_native_variance_failure_recovers_scale_invariant_score(
    scale, error_mode, interval
) -> None:
    returns = pd.Series(np.tile([0.01, 0.02, 0.03], 84) * scale)
    expected = _decimal_sample_sharpe(returns)
    with np.errstate(all=error_mode):
        if interval:
            ci = sharpe_confidence_interval(returns)
            assert ci is not None
            width = norm.isf(0.025) * math.sqrt(1 + expected**2 / 504)
            assert ci.lower == pytest.approx(expected - width, rel=5e-14, abs=0)
            assert ci.upper == pytest.approx(expected + width, rel=5e-14, abs=0)
        else:
            assert sharpe_ratio(returns) == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_nonconstant_native_mean_overflow_recovers_sample_score(error_mode) -> None:
    returns = pd.Series([1e308, 1.5e308] * 3)
    expected = _decimal_sample_sharpe(returns)
    with np.errstate(all=error_mode):
        assert sharpe_ratio(returns) == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize(
    "values",
    [
        [0.0, 0.0, -3e-264],
        [0.0, 0.0, 3e-264],
        [-1e200, 2e200, -3e200, 4e200],
        [-1e-200, 2e-200, -3e-200, 4e-200],
        [0.0, 0.0, -np.nextafter(0.0, 1.0)],
    ],
)
def test_native_first_recovery_matches_exact_float_decimal_oracle(values) -> None:
    returns = pd.Series(values)
    expected = _decimal_sample_sharpe(values)
    with np.errstate(all="raise"):
        assert sharpe_ratio(returns) == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("value", [0.1, 0.3, 1e308, 1e-200, 0.0])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_exact_constant_has_zero_sharpe_and_no_moment_evidence(value, dtype) -> None:
    returns = pd.Series([value] * 6, dtype=dtype)
    with np.errstate(all="raise"):
        assert sharpe_ratio(returns) == 0.0
        assert return_moments(returns) is None


def test_constant_iid_interval_uses_defined_zero_center() -> None:
    ci = sharpe_confidence_interval(pd.Series([0.1] * 252))
    assert ci is not None
    assert ci.assumption == "iid_normal"
    assert ci.lower == pytest.approx(-norm.isf(0.025))
    assert ci.upper == pytest.approx(norm.isf(0.025))


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_exact_constant_cannot_supply_normal_psr_moments(dtype) -> None:
    assert return_moments(pd.Series([0.1] * 6, dtype=dtype)) is None


def test_backtest_metrics_inherit_defined_constant_sharpe_and_interval() -> None:
    metrics = BacktestMetrics.from_series(pd.Series([0.1] * 252))
    assert metrics.sharpe == 0.0
    assert metrics.sharpe_ci is not None
    assert metrics.sharpe_ci.lower == pytest.approx(-norm.isf(0.025))
    assert metrics.sharpe_ci.upper == pytest.approx(norm.isf(0.025))


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_representable_signed_samples_match_independent_native_oracles(dtype) -> None:
    values = [-1.5, -1.0, 0.25, 2.0, 0.4, -0.3]
    returns = pd.Series(values, dtype=dtype)
    expected = math.sqrt(252) * np.mean(values) / np.std(values, ddof=1)
    assert sharpe_ratio(returns) == pytest.approx(expected)
    moments = return_moments(returns)
    assert moments is not None
    assert moments.n_returns == len(values)
    assert moments.skew == pytest.approx(pd.Series(values).skew())
    assert moments.kurtosis == pytest.approx(pd.Series(values).kurt() + 3)


def test_nearly_constant_sample_retains_native_sharpe() -> None:
    returns = pd.Series([0.1, np.nextafter(0.1, 1), 0.1] * 2)
    expected = float(np.sqrt(252) * returns.mean() / float(returns.std()))
    assert expected > 0
    assert sharpe_ratio(returns) == expected


@pytest.mark.parametrize("values", [[], [0.1]])
def test_valid_short_samples_keep_defined_absence(values) -> None:
    returns = pd.Series(values, dtype="Float64")
    assert sharpe_ratio(returns) == 0.0
    assert return_moments(returns) is None
    assert sharpe_confidence_interval(returns) is None
