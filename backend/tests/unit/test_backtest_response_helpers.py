import pandas as pd
import pytest

from app.api.v1.backtest import _equity_to_drawdown


def test_drawdown_curve_includes_pre_return_capital_baseline() -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D", tz="UTC")
    equity = pd.Series([90_000.0, 90_000.0], index=index)

    points = _equity_to_drawdown(equity, initial_equity=100_000.0)

    assert [point.drawdown for point in points] == pytest.approx([-0.10, -0.10])
