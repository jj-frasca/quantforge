"""ConnorsRSIStrategy: param validation; short-period (Wilder) RSI mean reversion — long when
deeply oversold, short when deeply overbought; signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.connors_rsi import ConnorsRSIStrategy


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


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        ConnorsRSIStrategy(window=1)


def test_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError, match="oversold"):
        ConnorsRSIStrategy(oversold=90.0, overbought=10.0)


def test_has_real_citation() -> None:
    assert any("Connors" in c for c in ConnorsRSIStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ConnorsRSIStrategy(window=2, oversold=10.0, overbought=90.0).parameters == {
        "window": 2,
        "oversold": 10.0,
        "overbought": 90.0,
    }


def test_short_signal_in_steady_uptrend() -> None:
    # Pure uptrend -> RSI pinned near 100 -> overbought -> fade with a short.
    close = pd.Series(np.linspace(50.0, 150.0, 80), name="close")
    signals = ConnorsRSIStrategy().generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_long_signal_in_steady_downtrend() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 80), name="close")
    signals = ConnorsRSIStrategy().generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_flat_price_stays_neutral() -> None:
    close = pd.Series(100.0, index=range(60), name="close")
    signals = ConnorsRSIStrategy().generate_signals(_frame(close))
    assert (signals == 0.0).all()  # constant price -> RSI undefined -> neutral 50 -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=7)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.4, name="close")
    signals = ConnorsRSIStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = ConnorsRSIStrategy().generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
