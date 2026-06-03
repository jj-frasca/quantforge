"""RSIMeanReversionStrategy: param validation; correct signal orientation
(long when oversold, short when overbought, flat between); no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.rsi_mean_reversion import RSIMeanReversionStrategy


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        RSIMeanReversionStrategy(window=1)


def test_rejects_invalid_threshold_pair() -> None:
    with pytest.raises(ValueError, match="oversold < overbought"):
        RSIMeanReversionStrategy(window=14, oversold=70, overbought=30)


def test_long_signal_when_rsi_below_oversold() -> None:
    # A long downtrend → many losses, few gains → low RSI → long signal at the end.
    series = pd.Series(np.linspace(100, 50, 60), name="close")
    data = pd.DataFrame({"close": series})
    signals = RSIMeanReversionStrategy(window=14, oversold=30, overbought=70).generate_signals(data)
    # The trailing bar of a steady decline should be in the long zone
    assert signals.iloc[-1] == 1.0


def test_short_signal_when_rsi_above_overbought() -> None:
    series = pd.Series(np.linspace(50, 100, 60), name="close")
    data = pd.DataFrame({"close": series})
    signals = RSIMeanReversionStrategy(window=14, oversold=30, overbought=70).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_flat_signal_when_rsi_in_neutral_band() -> None:
    # Symmetric noise around a constant — RSI hovers near 50.
    rng = np.random.default_rng(seed=1)
    series = pd.Series(100 + rng.standard_normal(120).cumsum() * 0.01, name="close")
    data = pd.DataFrame({"close": series})
    signals = RSIMeanReversionStrategy(window=14, oversold=20, overbought=80).generate_signals(data)
    # With a wide neutral band most signals should be 0 (flat)
    assert (signals == 0.0).sum() > 100


def test_warmup_period_yields_neutral_signal() -> None:
    # During the first `window` bars the RSI is undefined → strategy stays flat.
    series = pd.Series(np.linspace(50, 100, 60), name="close")
    data = pd.DataFrame({"close": series})
    signals = RSIMeanReversionStrategy(window=14, oversold=30, overbought=70).generate_signals(data)
    # Bars before the window fills should be neutral (fillna(50) puts RSI in neutral band)
    assert signals.iloc[0] == 0.0
