from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.fixtures.synthetic import builders

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import max_drawdown, sharpe_ratio, total_return
from app.research.frames import bars_to_frame
from app.research.strategies.sma import SMAStrategy


def _prices(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=index, dtype="float64")


def _trend(n: int = 50, start: float = 100.0, step: float = 0.001) -> pd.Series:
    return _prices([start * (1 + step) ** i for i in range(n)])


# --- §8 oracle tests ---


def test_buy_and_hold_matches_analytic_closed_form() -> None:
    prices = _trend(60)
    signals = pd.Series(1.0, index=prices.index)
    result = BacktestEngine(initial_capital=100_000.0, cost_rate=0.0).run(prices, signals)
    expected = 100_000.0 * prices / prices.iloc[0]
    assert np.allclose(result.equity_curve.to_numpy(), expected.to_numpy(), rtol=1e-9, atol=1e-6)


def test_zero_signal_produces_zero_exposure() -> None:
    prices = _trend(40)
    signals = pd.Series(0.0, index=prices.index)
    result = BacktestEngine(cost_rate=0.001).run(prices, signals)
    assert result.n_trades == 0
    assert result.metrics.total_return == pytest.approx(0.0)
    assert result.metrics.sharpe == 0.0
    assert np.allclose(result.equity_curve.to_numpy(), result.equity_curve.iloc[0])


def test_symmetric_long_short_nets_near_zero_without_costs() -> None:
    prices = _trend(60)
    signals = pd.Series(
        [1.0 if i % 2 == 0 else -1.0 for i in range(len(prices))], index=prices.index
    )
    result = BacktestEngine(cost_rate=0.0).run(prices, signals)
    assert abs(result.metrics.total_return) < 0.01


def test_transaction_cost_reduces_returns_monotonically() -> None:
    prices = _trend(60)
    signals = pd.Series(
        [1.0 if i % 2 == 0 else -1.0 for i in range(len(prices))], index=prices.index
    )
    returns = [
        BacktestEngine(cost_rate=c).run(prices, signals).metrics.total_return
        for c in (0.0, 0.001, 0.005, 0.01)
    ]
    for earlier, later in pairwise(returns):
        assert earlier >= later


def test_max_drawdown_is_in_unit_interval() -> None:
    prices = _prices([100, 90, 80, 120, 60, 130])
    signals = pd.Series(1.0, index=prices.index)
    result = BacktestEngine(cost_rate=0.0).run(prices, signals)
    assert -1.0 <= result.metrics.max_drawdown <= 0.0


def test_engine_rejects_bad_config() -> None:
    with pytest.raises(ValueError, match="capital"):
        BacktestEngine(initial_capital=0.0)
    with pytest.raises(ValueError, match="cost"):
        BacktestEngine(cost_rate=-0.1)


def test_run_strategy_executes_sma_end_to_end() -> None:
    frame = bars_to_frame(builders.clean_series(n=40))
    result = BacktestEngine(cost_rate=0.001).run_strategy(frame, SMAStrategy(fast=5, slow=10))
    assert len(result.equity_curve) == 40
    assert result.equity_curve.iloc[0] == pytest.approx(100_000.0)


def test_metrics_handle_empty_series() -> None:
    empty = pd.Series(dtype="float64")
    assert sharpe_ratio(empty) == 0.0
    assert max_drawdown(empty) == 0.0
    assert total_return(empty) == 0.0


# --- Hypothesis invariants ---


@given(
    # realistic bounded daily returns (the quality gate flags >20% moves); a price path
    # built from these keeps long-only net > -1, so equity stays strictly positive
    bar_returns=st.lists(
        st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=60,
    ),
    longs=st.lists(st.sampled_from([0.0, 1.0]), min_size=3, max_size=60),
)
def test_long_only_equity_is_finite_and_positive(
    bar_returns: list[float], longs: list[float]
) -> None:
    n = min(len(bar_returns), len(longs))
    price = 100.0
    closes = []
    for r in bar_returns[:n]:
        price *= 1 + r
        closes.append(price)
    prices = _prices(closes)
    signals = pd.Series(longs[:n], index=prices.index)
    result = BacktestEngine(cost_rate=0.001).run(prices, signals)
    eq = result.equity_curve.to_numpy()
    assert np.isfinite(eq).all()
    assert (eq > 0).all()
    assert -1.0 <= result.metrics.max_drawdown <= 0.0
