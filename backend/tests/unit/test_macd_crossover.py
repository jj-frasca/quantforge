"""MACDCrossoverStrategy: param validation; signal follows sign of histogram (MACD
above signal -> long, below -> short); EMA is causal (no look-ahead)."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.macd_crossover import MACDCrossoverStrategy


def test_rejects_invalid_fast_span() -> None:
    with pytest.raises(ValueError, match="fast EMA"):
        MACDCrossoverStrategy(fast=0, slow=26, signal=9)


def test_rejects_fast_not_less_than_slow() -> None:
    with pytest.raises(ValueError, match="fast EMA span must be < slow"):
        MACDCrossoverStrategy(fast=30, slow=26, signal=9)


def test_rejects_invalid_signal_span() -> None:
    with pytest.raises(ValueError, match="signal EMA"):
        MACDCrossoverStrategy(fast=12, slow=26, signal=0)


def test_long_signal_in_sustained_uptrend() -> None:
    # Steady uptrend: fast EMA exceeds slow EMA, MACD > 0, signal eventually catches up but
    # the trend keeps pushing MACD higher -> histogram > 0 -> long signal at the tail.
    series = pd.Series(np.linspace(50, 150, 200), name="close")
    data = pd.DataFrame({"close": series})
    signals = MACDCrossoverStrategy(fast=12, slow=26, signal=9).generate_signals(data)
    assert signals.iloc[-1] == 1.0


def test_short_signal_in_sustained_downtrend() -> None:
    series = pd.Series(np.linspace(150, 50, 200), name="close")
    data = pd.DataFrame({"close": series})
    signals = MACDCrossoverStrategy(fast=12, slow=26, signal=9).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_signal_is_in_minus_one_zero_one() -> None:
    # On any realistic price path, the discrete histogram-sign rule produces signals
    # only in {-1, 0, +1}. The §8 invariant for strategies is signal in [-1, 1].
    rng = np.random.default_rng(seed=3)
    series = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.3, name="close")
    data = pd.DataFrame({"close": series})
    signals = MACDCrossoverStrategy(fast=12, slow=26, signal=9).generate_signals(data)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


def test_no_look_ahead_appending_future_bar_does_not_change_past_signals() -> None:
    # EMA is causal: append a future bar and the signal series up to t-1 must stay
    # identical. If we accidentally used a centered or forward-looking smoother, this
    # would fail.
    series = pd.Series(np.linspace(50, 150, 100), name="close")
    data = pd.DataFrame({"close": series})
    base_signals = MACDCrossoverStrategy(fast=12, slow=26, signal=9).generate_signals(data)

    extended = pd.concat([series, pd.Series([200.0])], ignore_index=True)
    extended_data = pd.DataFrame({"close": extended})
    extended_signals = MACDCrossoverStrategy(fast=12, slow=26, signal=9).generate_signals(
        extended_data
    )

    pd.testing.assert_series_equal(
        base_signals.reset_index(drop=True),
        extended_signals.iloc[:-1].reset_index(drop=True),
    )
