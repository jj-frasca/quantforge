"""AroonStrategy: param validation; trend via time-since-extreme (long when a new high is more
recent than a new low, short when the reverse); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.aroon import AroonStrategy


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
        AroonStrategy(window=1)


def test_has_real_citation() -> None:
    assert any("Chande" in c for c in AroonStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert AroonStrategy(window=25).parameters == {"window": 25}


def test_long_signal_in_steady_uptrend() -> None:
    # Each new bar is a fresh high (Aroon-Up = 100) and the low is oldest (Aroon-Down = 0) -> long.
    close = pd.Series(np.linspace(50.0, 150.0, 60), name="close")
    signals = AroonStrategy(window=25).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_short_signal_in_steady_downtrend() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 60), name="close")
    signals = AroonStrategy(window=25).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_warmup_rows_are_flat() -> None:
    close = pd.Series(np.linspace(50.0, 150.0, 60), name="close")
    signals = AroonStrategy(window=25).generate_signals(_frame(close))
    assert (signals.iloc[:24] == 0.0).all()  # first window-1 bars have no full trailing window


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=13)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4, name="close")
    signals = AroonStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=26,
        max_size=100,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = AroonStrategy(window=25).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
