"""FiftyTwoWeekHighStrategy: param validation; George & Hwang (2004) nearness-to-52-week-high
momentum (long near the high, short far below it); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.fifty_two_week_high import FiftyTwoWeekHighStrategy


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
        FiftyTwoWeekHighStrategy(window=1)


def test_rejects_bad_threshold_pair() -> None:
    with pytest.raises(ValueError, match="threshold"):
        FiftyTwoWeekHighStrategy(near_high=0.7, near_low=0.9)  # low must be < high


def test_has_real_citation() -> None:
    assert any("George" in c for c in FiftyTwoWeekHighStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert FiftyTwoWeekHighStrategy(window=252, near_high=0.95, near_low=0.70).parameters == {
        "window": 252,
        "near_high": 0.95,
        "near_low": 0.70,
    }


def test_long_when_price_sits_at_its_trailing_high() -> None:
    close = pd.Series(np.linspace(50.0, 150.0, 300), name="close")  # always making new highs
    signals = FiftyTwoWeekHighStrategy(window=252).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_short_when_price_is_far_below_its_trailing_high() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 300), name="close")  # deep below the old high
    signals = FiftyTwoWeekHighStrategy(window=252).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_flat_in_the_middle_of_the_band() -> None:
    # Price at ~85% of its trailing high sits between near_low (0.70) and near_high (0.95) -> flat.
    close = pd.Series([100.0] * 260 + [85.0], name="close")
    signals = FiftyTwoWeekHighStrategy(window=252, near_high=0.95, near_low=0.70).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == 0.0


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=29)
    close = pd.Series(100 + rng.standard_normal(400).cumsum() * 0.4, name="close")
    signals = FiftyTwoWeekHighStrategy(window=252).generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = FiftyTwoWeekHighStrategy(window=20).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
