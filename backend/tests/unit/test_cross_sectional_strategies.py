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
    low_volatility_signal,
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


def _low_vol_panel(n_dates: int = 40) -> pd.DataFrame:
    # S_calm has tiny wiggles, S_wild has large ones -> S_calm must score highest on -realized-vol.
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    calm = 100.0 * np.cumprod(1.0 + np.full(n_dates, 0.0005))  # deterministic, near-zero vol
    rng = np.random.default_rng(7)
    wild = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.05, n_dates))
    mid = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.02, n_dates))
    return pd.DataFrame({"S_calm": calm, "S_wild": wild, "S_mid": mid}, index=idx)


def test_low_volatility_signal_negates_trailing_realized_vol() -> None:
    prices = _prices()
    sig = low_volatility_signal(prices, vol_window=3)
    returns = prices.pct_change()
    expected = -returns.rolling(3).std()
    pd.testing.assert_frame_equal(sig, expected)


def test_low_volatility_signal_warms_up_nan() -> None:
    prices = _prices()
    sig = low_volatility_signal(prices, vol_window=4)
    assert sig.iloc[:4].isna().all().all()  # first `vol_window` rows have no full return window
    assert sig.iloc[4:].notna().all().all()


def test_low_volatility_signal_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=12)
    full = low_volatility_signal(prices, vol_window=3)
    truncated = low_volatility_signal(prices.iloc[:8], vol_window=3)
    pd.testing.assert_frame_equal(full.iloc[:8], truncated)


def test_low_volatility_signal_ranks_calm_name_on_top() -> None:
    prices = _low_vol_panel()
    sig = low_volatility_signal(prices, vol_window=10)
    assert sig.iloc[-1].idxmax() == "S_calm"  # long the lowest-vol name
    assert sig.iloc[-1].idxmin() == "S_wild"  # short the highest-vol name


def test_default_strategies_are_price_only_without_scores() -> None:
    strategies = default_strategies()
    assert {"xs_momentum", "xs_reversal", "xs_low_volatility"} <= set(strategies)
    assert "xs_value" not in strategies
    assert all(isinstance(s, CrossSectionalStrategy) for s in strategies.values())
    assert all(len(s.param_grid) >= 1 for s in strategies.values())


def test_low_volatility_is_registered_with_multi_config_grid() -> None:
    low_vol = default_strategies()["xs_low_volatility"]
    assert len(low_vol.param_grid) >= 2  # >= 2 configs so PBO is meaningful
    assert all("vol_window" in p for p in low_vol.param_grid)
    panel = low_vol.build(low_vol.param_grid[0])(_prices())
    assert panel.shape == _prices().shape


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
