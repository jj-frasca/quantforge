"""TrueStrengthIndexStrategy: param validation; double-smoothed momentum oscillator (long when
TSI is positive, short when negative); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.true_strength_index import TrueStrengthIndexStrategy


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


def test_rejects_invalid_long_window() -> None:
    with pytest.raises(ValueError, match="long_window"):
        TrueStrengthIndexStrategy(long_window=1)


def test_rejects_invalid_short_window() -> None:
    with pytest.raises(ValueError, match="short_window"):
        TrueStrengthIndexStrategy(short_window=0)


def test_has_real_citation() -> None:
    assert any("Blau" in c for c in TrueStrengthIndexStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert TrueStrengthIndexStrategy(long_window=25, short_window=13).parameters == {
        "long_window": 25,
        "short_window": 13,
    }


def test_long_in_sustained_uptrend() -> None:
    close = pd.Series(100.0 + np.arange(120), dtype="float64")
    signals = TrueStrengthIndexStrategy().generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0  # positive double-smoothed momentum -> TSI > 0 -> long


def test_short_in_sustained_downtrend() -> None:
    close = pd.Series(300.0 - np.arange(120), dtype="float64")
    signals = TrueStrengthIndexStrategy().generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(80))
    signals = TrueStrengthIndexStrategy().generate_signals(_frame(close))
    assert (signals == 0.0).all()  # zero momentum -> 0/0 -> NaN -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=5)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5, dtype="float64")
    signals = TrueStrengthIndexStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


def test_no_lookahead_truncation_invariant() -> None:
    rng = np.random.default_rng(9)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.5, dtype="float64")
    s = TrueStrengthIndexStrategy()
    full = s.generate_signals(_frame(close))
    trunc = s.generate_signals(_frame(close.iloc[:150]))
    pd.testing.assert_series_equal(full.iloc[:150], trunc, check_names=False)


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=40,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = TrueStrengthIndexStrategy().generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
