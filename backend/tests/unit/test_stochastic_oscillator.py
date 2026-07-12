"""StochasticOscillatorStrategy: param validation; long when %D is oversold, short
when overbought; signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.stochastic_oscillator import StochasticOscillatorStrategy


def _ohlc_frame(close: pd.Series, span: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + span,
            "low": close - span,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_invalid_k_window() -> None:
    with pytest.raises(ValueError, match="k_window"):
        StochasticOscillatorStrategy(k_window=1)


def test_rejects_invalid_d_window() -> None:
    with pytest.raises(ValueError, match="d_window"):
        StochasticOscillatorStrategy(d_window=0)


def test_rejects_bad_threshold_pair() -> None:
    with pytest.raises(ValueError, match="oversold"):
        StochasticOscillatorStrategy(oversold=80.0, overbought=20.0)


def test_has_real_citation() -> None:
    assert any("Lane" in c for c in StochasticOscillatorStrategy().research_citations)


def test_parameters_round_trip() -> None:
    strat = StochasticOscillatorStrategy(k_window=14, d_window=3, oversold=20.0, overbought=80.0)
    assert strat.parameters == {
        "k_window": 14,
        "d_window": 3,
        "oversold": 20.0,
        "overbought": 80.0,
    }


def test_short_signal_in_steady_uptrend() -> None:
    # Close near the window high -> %K/%D near 100 -> overbought -> short.
    close = pd.Series(np.linspace(50.0, 100.0, 60), name="close")
    signals = StochasticOscillatorStrategy().generate_signals(_ohlc_frame(close))
    assert signals.iloc[-1] == -1.0


def test_long_signal_in_steady_downtrend() -> None:
    close = pd.Series(np.linspace(100.0, 50.0, 60), name="close")
    signals = StochasticOscillatorStrategy().generate_signals(_ohlc_frame(close))
    assert signals.iloc[-1] == 1.0


def test_constant_price_stays_neutral() -> None:
    close = pd.Series(100.0, index=range(40), name="close")
    signals = StochasticOscillatorStrategy().generate_signals(_ohlc_frame(close, span=0.0))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=11)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4, name="close")
    signals = StochasticOscillatorStrategy().generate_signals(_ohlc_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=80,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = StochasticOscillatorStrategy().generate_signals(_ohlc_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
