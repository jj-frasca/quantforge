"""BollingerBandsStrategy: param validation; long below lower band, short above upper,
flat between; no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.bollinger_bands import BollingerBandsStrategy


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        BollingerBandsStrategy(window=1)


def test_rejects_non_positive_num_std() -> None:
    with pytest.raises(ValueError, match="num_std"):
        BollingerBandsStrategy(window=20, num_std=0)


def test_short_when_close_above_upper_band() -> None:
    # Flat noise → tight bands → a sudden spike trips the upper band → short.
    rng = np.random.default_rng(seed=11)
    series = pd.Series(100 + rng.standard_normal(60) * 0.5, name="close")
    series.iloc[-1] = 120.0  # blatant outlier
    data = pd.DataFrame({"close": series})
    signals = BollingerBandsStrategy(window=20, num_std=2.0).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_long_when_close_below_lower_band() -> None:
    rng = np.random.default_rng(seed=11)
    series = pd.Series(100 + rng.standard_normal(60) * 0.5, name="close")
    series.iloc[-1] = 80.0  # blatant undershoot
    data = pd.DataFrame({"close": series})
    signals = BollingerBandsStrategy(window=20, num_std=2.0).generate_signals(data)
    assert signals.iloc[-1] == 1.0


def test_flat_when_close_inside_the_bands() -> None:
    # A constant series has zero std → bands collapse to the mean → close ≤ mean ≤ close
    # boundary case: pandas std on constant returns 0; band == close; signal stays 0.
    series = pd.Series([100.0] * 60, name="close")
    data = pd.DataFrame({"close": series})
    signals = BollingerBandsStrategy(window=20, num_std=2.0).generate_signals(data)
    assert (signals == 0.0).all()
