"""ResidualMomentumStrategy: param validation; momentum of DE-TRENDED (idiosyncratic) returns —
long when recent returns run above the name's own trailing drift, short when below; signals in
{-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.residual_momentum import ResidualMomentumStrategy


def _frame(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def _from_daily_returns(daily: np.ndarray) -> pd.Series:
    prices = 100.0 * np.cumprod(1.0 + daily)
    idx = pd.date_range("2015-01-01", periods=len(prices), freq="B", tz="UTC")
    return pd.Series(prices, index=idx, name="close")


def test_rejects_invalid_lookback() -> None:
    with pytest.raises(ValueError, match="lookback"):
        ResidualMomentumStrategy(lookback=0)


def test_rejects_invalid_mean_window() -> None:
    with pytest.raises(ValueError, match="mean_window"):
        ResidualMomentumStrategy(mean_window=1)


def test_has_real_citation() -> None:
    assert any("Blitz" in c for c in ResidualMomentumStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ResidualMomentumStrategy(lookback=120, skip=20, mean_window=60).parameters == {
        "lookback": 120,
        "skip": 20,
        "mean_window": 60,
    }


def test_constant_drift_is_flat() -> None:
    # A pure constant drift = zero residual (returns equal their own trailing mean) -> flat.
    close = _from_daily_returns(np.full(400, 0.0008))
    signals = ResidualMomentumStrategy(lookback=120, skip=20, mean_window=60).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == 0.0


def test_long_when_returns_accelerate_above_trend() -> None:
    # Returns rising over time -> recent returns exceed the trailing mean -> positive residual -> long.
    close = _from_daily_returns(np.linspace(-0.001, 0.003, 400))
    signals = ResidualMomentumStrategy(lookback=120, skip=20, mean_window=60).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == 1.0


def test_short_when_returns_decelerate_below_trend() -> None:
    close = _from_daily_returns(np.linspace(0.003, -0.001, 400))
    signals = ResidualMomentumStrategy(lookback=120, skip=20, mean_window=60).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == -1.0


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=41)
    close = pd.Series(100 + rng.standard_normal(400).cumsum() * 0.4, name="close")
    signals = ResidualMomentumStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=5.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = ResidualMomentumStrategy(lookback=20, skip=2, mean_window=10).generate_signals(
        _frame(close)
    )
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
