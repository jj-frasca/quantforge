"""UltimateOscillatorStrategy: param validation; Larry Williams' three-timeframe buying-pressure
oscillator traded as mean reversion (long oversold, short overbought); signals in {-1, 0, 1};
no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.ultimate_oscillator import UltimateOscillatorStrategy


def _hlc_frame(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def _flat_band(close_at: str, n: int = 40) -> pd.DataFrame:
    idx = pd.RangeIndex(n)
    high = pd.Series(101.0, index=idx)
    low = pd.Series(99.0, index=idx)
    close = {"high": high, "low": low, "mid": pd.Series(100.0, index=idx)}[close_at]
    return _hlc_frame(high, low, close.copy())


def test_rejects_bad_threshold_pair() -> None:
    with pytest.raises(ValueError, match="oversold"):
        UltimateOscillatorStrategy(oversold=70.0, overbought=30.0)


def test_has_real_citation() -> None:
    assert any("Williams" in c for c in UltimateOscillatorStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert UltimateOscillatorStrategy(oversold=30.0, overbought=70.0).parameters == {
        "oversold": 30.0,
        "overbought": 70.0,
    }


def test_long_when_closes_pin_to_the_low() -> None:
    # close == low every bar -> buying pressure ~0 -> UO ~0 -> oversold -> long.
    signals = UltimateOscillatorStrategy().generate_signals(_flat_band("low"))
    assert signals.iloc[-1] == 1.0


def test_short_when_closes_pin_to_the_high() -> None:
    # close == high every bar -> buying pressure ~ full range -> UO ~100 -> overbought -> short.
    signals = UltimateOscillatorStrategy().generate_signals(_flat_band("high"))
    assert signals.iloc[-1] == -1.0


def test_flat_when_closes_sit_mid_range() -> None:
    signals = UltimateOscillatorStrategy().generate_signals(_flat_band("mid"))
    assert signals.iloc[-1] == 0.0  # UO ~50, between the thresholds


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=31)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4)
    signals = UltimateOscillatorStrategy().generate_signals(
        _hlc_frame(close + 0.5, close - 0.5, close)
    )
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=100,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = UltimateOscillatorStrategy().generate_signals(
        _hlc_frame(close + 0.5, close - 0.5, close)
    )
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
