"""ChandeMomentumStrategy: param validation; Chande Momentum Oscillator traded as mean reversion
(long oversold, short overbought); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.chande_momentum import ChandeMomentumStrategy


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
        ChandeMomentumStrategy(window=1)


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        ChandeMomentumStrategy(threshold=0.0)
    with pytest.raises(ValueError, match="threshold"):
        ChandeMomentumStrategy(threshold=100.0)


def test_has_real_citation() -> None:
    assert any("Chande" in c for c in ChandeMomentumStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ChandeMomentumStrategy(window=14, threshold=50.0).parameters == {
        "window": 14,
        "threshold": 50.0,
    }


def test_short_after_a_persistent_rally() -> None:
    # All up moves -> CMO = +100 (overbought) -> mean reversion fades it -> short.
    close = pd.Series(100.0 + np.arange(60), dtype="float64")
    signals = ChandeMomentumStrategy(window=14, threshold=50.0).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_long_after_a_persistent_selloff() -> None:
    close = pd.Series(300.0 - np.arange(60), dtype="float64")
    signals = ChandeMomentumStrategy(window=14, threshold=50.0).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(60))
    signals = ChandeMomentumStrategy(window=14, threshold=50.0).generate_signals(_frame(close))
    assert (signals == 0.0).all()  # no up/down moves -> 0/0 -> NaN -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=8)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5, dtype="float64")
    signals = ChandeMomentumStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


def test_no_lookahead_truncation_invariant() -> None:
    rng = np.random.default_rng(2)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.5, dtype="float64")
    s = ChandeMomentumStrategy(window=14, threshold=50.0)
    full = s.generate_signals(_frame(close))
    trunc = s.generate_signals(_frame(close.iloc[:150]))
    pd.testing.assert_series_equal(full.iloc[:150], trunc, check_names=False)


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = ChandeMomentumStrategy(window=14, threshold=50.0).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
