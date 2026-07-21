"""OvernightGapStrategy: param validation; fade the overnight open gap (short big up-gaps, long big
down-gaps); signals in {-1, 0, 1}; no look-ahead (the gap at t uses open_t and close_{t-1}, both
known at t's open)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.overnight_gap import OvernightGapStrategy


def _frame(open_: pd.Series, close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": open_,
            "high": pd.concat([open_, close], axis=1).max(axis=1) + 0.5,
            "low": pd.concat([open_, close], axis=1).min(axis=1) - 0.5,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        OvernightGapStrategy(threshold=0.0)


def test_has_real_citation() -> None:
    assert any("Lou" in c for c in OvernightGapStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert OvernightGapStrategy(threshold=0.02).parameters == {"threshold": 0.02}


def test_shorts_a_large_up_gap() -> None:
    # open opens 5% above the prior close -> fade the gap -> short.
    close = pd.Series([100.0, 100.0, 100.0], name="close")
    open_ = pd.Series([100.0, 100.0, 105.0], name="open")  # last bar gaps up
    signals = OvernightGapStrategy(threshold=0.02).generate_signals(_frame(open_, close))
    assert signals.iloc[-1] == -1.0


def test_longs_a_large_down_gap() -> None:
    close = pd.Series([100.0, 100.0, 100.0], name="close")
    open_ = pd.Series([100.0, 100.0, 95.0], name="open")  # last bar gaps down
    signals = OvernightGapStrategy(threshold=0.02).generate_signals(_frame(open_, close))
    assert signals.iloc[-1] == 1.0


def test_flat_on_a_small_gap() -> None:
    close = pd.Series([100.0, 100.0, 100.0], name="close")
    open_ = pd.Series([100.0, 100.0, 100.5], name="open")  # 0.5% gap < 2% threshold
    signals = OvernightGapStrategy(threshold=0.02).generate_signals(_frame(open_, close))
    assert signals.iloc[-1] == 0.0


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=43)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4, name="close")
    open_ = close.shift(1).fillna(close) * (1 + rng.normal(0, 0.01, 200))
    signals = OvernightGapStrategy().generate_signals(_frame(open_, close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=5.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=80,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    open_ = close.shift(1).fillna(close)
    signals = OvernightGapStrategy(threshold=0.02).generate_signals(_frame(open_, close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
