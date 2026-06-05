"""TrendFilteredMeanReversionStrategy: param validation; long oversold-in-uptrend,
short overbought-in-downtrend; flat when the trend disagrees with the z-score signal."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.trend_filtered_mean_reversion import (
    TrendFilteredMeanReversionStrategy,
)


def test_rejects_invalid_z_window() -> None:
    with pytest.raises(ValueError, match="z_window"):
        TrendFilteredMeanReversionStrategy(z_window=1)


def test_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="z_threshold"):
        TrendFilteredMeanReversionStrategy(z_threshold=0)


def test_rejects_invalid_trend_window() -> None:
    with pytest.raises(ValueError, match="trend_window must be >= 2"):
        TrendFilteredMeanReversionStrategy(trend_window=1)


def test_rejects_trend_window_not_greater_than_z_window() -> None:
    # The "trend" must be the LONGER view — otherwise the strategy degenerates.
    with pytest.raises(ValueError, match="longer view"):
        TrendFilteredMeanReversionStrategy(z_window=50, trend_window=20)


def test_long_signal_on_oversold_dip_within_uptrend() -> None:
    # Construct a series that satisfies BOTH conditions at the final bar:
    #   1. close > trend SMA (uptrend): long-term avg is low, recent prices are high.
    #   2. z-score deeply negative (oversold): recent rolling mean is well above current.
    # Note: a single-bar dip in a steady linspace doesn't show as deeply oversold because
    # the rolling mean and std include the dip itself — the new value is "close to the
    # new normal" by construction. We need a multi-bar high plateau followed by a drop
    # so the recent rolling mean is dominated by the plateau, not the dip.
    prices = [80.0] * 180 + [120.0] * 19 + [110.0]  # low base, recent peak, final dip
    data = pd.DataFrame({"close": pd.Series(prices)})
    signals = TrendFilteredMeanReversionStrategy(
        z_window=20, z_threshold=1.0, trend_window=100
    ).generate_signals(data)
    assert signals.iloc[-1] == 1.0


def test_short_signal_on_overbought_pop_within_downtrend() -> None:
    # Mirror of the long case: high base, recent valley, final pop.
    prices = [120.0] * 180 + [80.0] * 19 + [90.0]
    data = pd.DataFrame({"close": pd.Series(prices)})
    signals = TrendFilteredMeanReversionStrategy(
        z_window=20, z_threshold=1.0, trend_window=100
    ).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_no_signal_when_trend_disagrees() -> None:
    # Oversold dip in a DOWNTREND — the trend filter should suppress the long signal
    # (this is the "falling knife" guard).
    series = pd.Series(np.linspace(150, 50, 200), name="close")
    # Last bar deeply oversold relative to short-window mean, but in a downtrend.
    series.iloc[-1] = 30.0
    data = pd.DataFrame({"close": series})
    signals = TrendFilteredMeanReversionStrategy(
        z_window=20, z_threshold=1.0, trend_window=100
    ).generate_signals(data)
    # Should NOT be long despite the oversold reading — that's the whole point.
    assert signals.iloc[-1] != 1.0


def test_warmup_region_is_flat() -> None:
    series = pd.Series(np.linspace(50, 150, 200), name="close")
    data = pd.DataFrame({"close": series})
    signals = TrendFilteredMeanReversionStrategy(
        z_window=20, z_threshold=1.0, trend_window=100
    ).generate_signals(data)
    # Bars before either window fills must be flat.
    assert signals.iloc[0] == 0.0
    assert signals.iloc[50] == 0.0


def test_signal_set_is_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=7)
    series = pd.Series(100 + rng.standard_normal(400).cumsum() * 0.5, name="close")
    data = pd.DataFrame({"close": series})
    signals = TrendFilteredMeanReversionStrategy().generate_signals(data)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})
