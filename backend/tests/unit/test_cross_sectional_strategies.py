"""Cross-sectional signal producers + registry (ADR-024). Each strategy maps a price panel to a
signal panel where `signal[t, sym]` uses only prices <= t (built with `.shift`), so the engine's
no-lookahead contract holds. Momentum longs past winners, reversal longs recent losers, value ranks
on each name's (as-of) UndervaluationScore."""

import numpy as np
import pandas as pd

from app.research.cross_sectional.registry import (
    CrossSectionalStrategy,
    default_strategies,
)
from app.research.cross_sectional.strategies import (
    momentum_signal,
    reversal_signal,
    value_signal,
)


def _prices(n_dates: int = 8, n_symbols: int = 3, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.01, (n_dates, n_symbols)), axis=0)
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def test_momentum_signal_is_trailing_return_and_warms_up_nan() -> None:
    prices = _prices()
    sig = momentum_signal(prices, lookback=3, skip=0)
    assert sig.iloc[:3].isna().all().all()  # first `lookback` rows have no trailing window
    expected = prices.iloc[3] / prices.iloc[0] - 1.0
    pd.testing.assert_series_equal(sig.iloc[3], expected, check_names=False)


def test_momentum_signal_skip_shifts_the_window_back() -> None:
    prices = _prices()
    sig = momentum_signal(prices, lookback=2, skip=1)
    assert sig.iloc[:3].isna().all().all()  # lookback + skip = 3 warmup rows
    expected = prices.iloc[2] / prices.iloc[0] - 1.0  # ends `skip` bars ago
    pd.testing.assert_series_equal(sig.iloc[3], expected, check_names=False)


def test_reversal_signal_is_negated_trailing_return() -> None:
    prices = _prices()
    pd.testing.assert_frame_equal(
        reversal_signal(prices, lookback=3), -momentum_signal(prices, lookback=3, skip=0)
    )


def test_value_signal_broadcasts_static_scores_across_dates() -> None:
    prices = _prices(n_symbols=3)
    scores = {"S0": 0.8, "S1": 0.2}  # S2 unscored
    sig = value_signal(prices, scores)
    assert sig.shape == prices.shape
    assert (sig["S0"] == 0.8).all() and (sig["S1"] == 0.2).all()
    assert sig["S2"].isna().all()  # unscored name -> NaN -> excluded by the ranker


def test_default_strategies_are_price_only_without_scores() -> None:
    strategies = default_strategies()
    assert set(strategies) == {"xs_momentum", "xs_reversal"}
    assert all(isinstance(s, CrossSectionalStrategy) for s in strategies.values())
    assert all(len(s.param_grid) >= 1 for s in strategies.values())


def test_default_strategies_add_value_when_scores_given() -> None:
    strategies = default_strategies(value_scores={"S0": 0.8, "S1": 0.2})
    assert "xs_value" in strategies


def test_strategy_build_produces_a_working_signal_panel() -> None:
    prices = _prices()
    mom = default_strategies()["xs_momentum"]
    signal_fn = mom.build(mom.param_grid[0])
    panel = signal_fn(prices)
    assert panel.shape == prices.shape


def test_value_strategy_build_uses_the_scores() -> None:
    prices = _prices()
    value = default_strategies(value_scores={"S0": 0.9})["xs_value"]
    panel = value.build(value.param_grid[0])(prices)
    assert (panel["S0"] == 0.9).all()
