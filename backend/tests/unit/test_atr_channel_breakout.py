"""ATRChannelBreakoutStrategy: param validation; breakout of an ATR-width channel around an SMA,
holding the trend (carry-forward) until the opposite band breaks; signals in {-1, 0, 1};
no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.atr_channel_breakout import ATRChannelBreakoutStrategy


def _ohlcv(close: pd.Series, spread: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_ma_window_below_two() -> None:
    with pytest.raises(ValueError, match="ma_window"):
        ATRChannelBreakoutStrategy(ma_window=1)


def test_rejects_atr_window_below_two() -> None:
    with pytest.raises(ValueError, match="atr_window"):
        ATRChannelBreakoutStrategy(atr_window=1)


def test_rejects_non_positive_multiplier() -> None:
    with pytest.raises(ValueError, match="multiplier"):
        ATRChannelBreakoutStrategy(multiplier=0.0)


def test_has_real_citation() -> None:
    assert any("Kaufman" in c for c in ATRChannelBreakoutStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ATRChannelBreakoutStrategy(ma_window=20, atr_window=14, multiplier=2.0).parameters == {
        "ma_window": 20,
        "atr_window": 14,
        "multiplier": 2.0,
    }


def test_long_on_sustained_uptrend() -> None:
    close = pd.Series(100.0 + np.arange(60), dtype="float64")
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 1.0


def test_short_on_sustained_downtrend() -> None:
    close = pd.Series(200.0 - np.arange(60), dtype="float64")
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == -1.0


def test_carries_long_forward_when_price_holds_after_breakout() -> None:
    # Break upward, then a mild drift that stays inside the channel must CARRY the long
    # (unlike Keltner, which reverts to flat between the bands).
    up = 100.0 + np.arange(40)
    hold = np.full(6, 133.0)  # a mild pullback that sits INSIDE the channel
    close = pd.Series(np.concatenate([up, hold]), dtype="float64")
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 1.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(60))
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=13)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5)
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close, spread=1.0))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = ATRChannelBreakoutStrategy().generate_signals(_ohlcv(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
