"""TRIXStrategy: param validation; triple-smoothed EMA momentum (long when the smoothed rate of
change is positive, short when negative); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.trix import TRIXStrategy


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
        TRIXStrategy(window=1)


def test_rejects_invalid_signal() -> None:
    with pytest.raises(ValueError, match="signal"):
        TRIXStrategy(signal=0)


def test_has_real_citation() -> None:
    assert any("Hutson" in c for c in TRIXStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert TRIXStrategy(window=15, signal=9).parameters == {"window": 15, "signal": 9}


def test_long_signal_in_steady_uptrend() -> None:
    close = pd.Series(np.linspace(50.0, 150.0, 120), name="close")
    signals = TRIXStrategy(window=15, signal=9).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0  # rising triple EMA -> positive TRIX -> long


def test_short_signal_in_steady_downtrend() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 120), name="close")
    signals = TRIXStrategy(window=15, signal=9).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_flat_price_stays_neutral() -> None:
    close = pd.Series(100.0, index=range(80), name="close")
    signals = TRIXStrategy(window=15, signal=9).generate_signals(_frame(close))
    assert (signals == 0.0).all()  # constant price -> zero rate of change -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=11)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.4, name="close")
    signals = TRIXStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = TRIXStrategy(window=15, signal=9).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
