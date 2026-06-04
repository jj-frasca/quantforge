"""KeltnerChannelStrategy: param validation; uses OHLC (high/low/close); breakout
above upper -> long, below lower -> short; no carry-forward; no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.keltner_channel import KeltnerChannelStrategy


def _ohlc_frame(
    close: pd.Series, high_offset: float = 0.5, low_offset: float = 0.5
) -> pd.DataFrame:
    """Build an OHLC frame from a close series; high/low are constant offsets from close."""
    return pd.DataFrame(
        {
            "open": close,
            "high": close + high_offset,
            "low": close - low_offset,
            "close": close,
            "volume": pd.Series(1_000_000, index=close.index, dtype="float64"),
        },
        index=close.index,
    )


def test_rejects_invalid_ma_window() -> None:
    with pytest.raises(ValueError, match="ma_window"):
        KeltnerChannelStrategy(ma_window=0)


def test_rejects_invalid_atr_window() -> None:
    with pytest.raises(ValueError, match="atr_window"):
        KeltnerChannelStrategy(atr_window=1)


def test_rejects_non_positive_multiplier() -> None:
    with pytest.raises(ValueError, match="multiplier"):
        KeltnerChannelStrategy(multiplier=0)


def test_long_signal_on_breakout_above_upper_band() -> None:
    # Quiet noise, then a spike: ATR is small, midline is near 100, spike to 130 breaks
    # the upper band cleanly.
    rng = np.random.default_rng(seed=2)
    close = pd.Series(100 + rng.standard_normal(60) * 0.3, name="close")
    close.iloc[-1] = 130.0
    data = _ohlc_frame(close)
    signals = KeltnerChannelStrategy(ma_window=20, atr_window=14, multiplier=2.0).generate_signals(
        data
    )
    assert signals.iloc[-1] == 1.0


def test_short_signal_on_breakout_below_lower_band() -> None:
    rng = np.random.default_rng(seed=2)
    close = pd.Series(100 + rng.standard_normal(60) * 0.3, name="close")
    close.iloc[-1] = 70.0
    data = _ohlc_frame(close)
    signals = KeltnerChannelStrategy(ma_window=20, atr_window=14, multiplier=2.0).generate_signals(
        data
    )
    assert signals.iloc[-1] == -1.0


def test_no_carry_forward_between_bands() -> None:
    # A breakout long, then the close returns to the mean — signal should drop back to 0.
    # (Distinction from Donchian which DOES carry the position forward.)
    base = pd.Series(100 + np.zeros(60), name="close")
    base.iloc[40] = 130.0  # one-bar breakout
    base.iloc[41:] = 100.0  # back inside the channel
    data = _ohlc_frame(base)
    signals = KeltnerChannelStrategy(ma_window=20, atr_window=14, multiplier=2.0).generate_signals(
        data
    )
    # Final bar after the spike must be 0 (flat), not still long
    assert signals.iloc[-1] == 0.0


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=4)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4, name="close")
    data = _ohlc_frame(close)
    signals = KeltnerChannelStrategy().generate_signals(data)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})
