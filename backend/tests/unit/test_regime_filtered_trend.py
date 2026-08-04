"""RegimeFilteredTrendStrategy: param validation; a genuine 2-signal COMBINATION -- an SMA
crossover taken only when Wilder's ADX confirms a strong-enough trend regime; signals in
{-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.regime_filtered_trend import RegimeFilteredTrendStrategy


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


def test_rejects_fast_below_one() -> None:
    with pytest.raises(ValueError, match="fast"):
        RegimeFilteredTrendStrategy(fast=0)


def test_rejects_fast_not_below_slow() -> None:
    with pytest.raises(ValueError, match="slow"):
        RegimeFilteredTrendStrategy(fast=50, slow=20)


def test_rejects_adx_window_below_two() -> None:
    with pytest.raises(ValueError, match="adx_window"):
        RegimeFilteredTrendStrategy(adx_window=1)


def test_rejects_adx_threshold_out_of_range() -> None:
    with pytest.raises(ValueError, match="adx_threshold"):
        RegimeFilteredTrendStrategy(adx_threshold=0.0)


def test_has_real_citation() -> None:
    assert any("Wilder" in c for c in RegimeFilteredTrendStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert RegimeFilteredTrendStrategy(
        fast=20, slow=50, adx_window=14, adx_threshold=25.0
    ).parameters == {
        "fast": 20,
        "slow": 50,
        "adx_window": 14,
        "adx_threshold": 25.0,
    }


def test_long_in_strong_uptrend() -> None:
    close = pd.Series(100.0 + np.arange(80), dtype="float64")
    signals = RegimeFilteredTrendStrategy(
        fast=10, slow=20, adx_window=14, adx_threshold=25.0
    ).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 1.0


def test_short_in_strong_downtrend() -> None:
    close = pd.Series(300.0 - np.arange(80), dtype="float64")
    signals = RegimeFilteredTrendStrategy(
        fast=10, slow=20, adx_window=14, adx_threshold=25.0
    ).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == -1.0


def test_regime_filter_vetoes_the_crossover_in_a_rangebound_market() -> None:
    # A choppy, rangebound oscillation produces frequent SMA crossovers but a LOW ADX (no
    # sustained trend). With a normal threshold the regime gate vetoes every crossover -> flat.
    # This isolates the combination: the crossover alone would trade the chop; the ADX gate sits
    # it out. (A perfectly clean linear ramp is a poor veto demo -- its ADX approaches ~100.)
    idx = pd.RangeIndex(200)
    close = pd.Series(100.0 + 2.0 * np.sin(np.arange(200) * 0.6), index=idx)
    signals = RegimeFilteredTrendStrategy(
        fast=10, slow=20, adx_window=14, adx_threshold=40.0
    ).generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(80))
    signals = RegimeFilteredTrendStrategy(fast=10, slow=20).generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=19)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5)
    signals = RegimeFilteredTrendStrategy().generate_signals(_ohlcv(close, spread=1.0))
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
    signals = RegimeFilteredTrendStrategy(fast=5, slow=10, adx_window=7).generate_signals(
        _ohlcv(close)
    )
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
