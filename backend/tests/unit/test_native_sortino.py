"""Sortino recovery, representability and required nullable wire evidence."""

from dataclasses import asdict
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.api.v1.backtest import BacktestMetricsView
from app.research.backtesting.metrics import BacktestMetrics, sortino_ratio


def decimal_sortino(values, target=0.0) -> Decimal:
    with localcontext() as context:
        context.prec = 90
        observations = [Decimal.from_float(float(value)) for value in values]
        threshold = Decimal.from_float(float(target))
        excess = [value - threshold for value in observations]
        semi_variance = sum(min(value, Decimal(0)) ** 2 for value in excess) / len(excess)
        return Decimal(252).sqrt() * (sum(excess) / len(excess)) / semi_variance.sqrt()


@pytest.mark.parametrize("scale", [1.0, 1e200, 1e-200])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_sortino_scale_recovery_matches_decimal_score(scale, error_mode, dtype) -> None:
    returns = pd.Series(np.array([-0.01, 0.02, -0.03, 0.04]) * scale, dtype=dtype)
    expected = float(decimal_sortino(returns))
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns)
    assert actual == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("target", [1e308, -1e308])
def test_sortino_normalizes_target_before_excess_overflow(target) -> None:
    returns = pd.Series([-1e308, -1.5e308])
    with np.errstate(all="raise"):
        actual = sortino_ratio(returns, target=target)
    assert actual == pytest.approx(float(decimal_sortino(returns, target)), rel=5e-14, abs=0)


@pytest.mark.parametrize("downside", [-1e-200, -1e-300])
def test_sortino_recovers_asymmetric_representable_downside(downside) -> None:
    returns = pd.Series([downside, 1.0])
    with np.errstate(all="raise"):
        actual = sortino_ratio(returns)
    assert actual == pytest.approx(float(decimal_sortino(returns)), rel=5e-14, abs=0)


def test_sortino_true_overflow_is_unmeasured_not_no_downside() -> None:
    returns = pd.Series([-np.nextafter(0.0, 1.0), 1.0])
    assert decimal_sortino(returns) > Decimal.from_float(np.finfo(float).max)
    with np.errstate(all="raise"):
        assert sortino_ratio(returns) is None


def test_engine_metrics_and_wire_keep_unmeasured_sortino_without_losing_returns() -> None:
    metrics = BacktestMetrics.from_series(pd.Series([-np.nextafter(0.0, 1.0), 1.0]))
    assert metrics.sortino is None
    assert metrics.total_return == pytest.approx(1.0)
    view = BacktestMetricsView.model_validate(asdict(metrics))
    assert view.model_dump(mode="json")["sortino"] is None


def test_backtest_metric_wire_accepts_explicit_unmeasured_value() -> None:
    values = asdict(BacktestMetrics.from_series(pd.Series([0.0, 0.0])))
    values["sortino"] = None
    assert BacktestMetricsView.model_validate(values).model_dump(mode="json")["sortino"] is None


@pytest.mark.parametrize("values", [[], [0.01], [0.0, 0.01, 0.02]])
def test_sortino_measured_short_no_downside_remains_zero(values) -> None:
    assert sortino_ratio(pd.Series(values, dtype="Float64")) == 0.0


@pytest.mark.parametrize("sortino", [float("nan"), float("inf"), -float("inf")])
def test_backtest_metric_wire_rejects_nonfinite_sortino(sortino) -> None:
    values = asdict(BacktestMetrics.from_series(pd.Series([0.0, 0.0])))
    values["sortino"] = sortino
    with pytest.raises(ValidationError, match="finite"):
        BacktestMetricsView.model_validate(values)


def test_backtest_metric_wire_requires_sortino_key() -> None:
    values = asdict(BacktestMetrics.from_series(pd.Series([0.0, 0.0])))
    del values["sortino"]
    with pytest.raises(ValidationError, match="required"):
        BacktestMetricsView.model_validate(values)
