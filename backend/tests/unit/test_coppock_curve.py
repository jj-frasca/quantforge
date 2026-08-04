"""CoppockCurveStrategy: param validation; long-term momentum via a weighted MA of summed
rate-of-change (long above zero, short below); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.coppock_curve import CoppockCurveStrategy


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


def test_rejects_roc_short_below_one() -> None:
    with pytest.raises(ValueError, match="roc_short"):
        CoppockCurveStrategy(roc_short=0)


def test_rejects_bad_roc_pair() -> None:
    with pytest.raises(ValueError, match="roc"):
        CoppockCurveStrategy(roc_long=10, roc_short=14)  # long must be > short


def test_rejects_invalid_wma_window() -> None:
    with pytest.raises(ValueError, match="wma_window"):
        CoppockCurveStrategy(wma_window=1)


def test_has_real_citation() -> None:
    assert any("Coppock" in c for c in CoppockCurveStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert CoppockCurveStrategy(roc_long=14, roc_short=11, wma_window=10).parameters == {
        "roc_long": 14,
        "roc_short": 11,
        "wma_window": 10,
    }


def test_long_in_sustained_uptrend() -> None:
    close = pd.Series(100.0 * (1.003 ** np.arange(120)), dtype="float64")
    signals = CoppockCurveStrategy(roc_long=14, roc_short=11, wma_window=10).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == 1.0  # positive long-term momentum -> Coppock > 0 -> long


def test_short_in_sustained_downtrend() -> None:
    close = pd.Series(300.0 * (0.997 ** np.arange(120)), dtype="float64")
    signals = CoppockCurveStrategy(roc_long=14, roc_short=11, wma_window=10).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] == -1.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(80))
    signals = CoppockCurveStrategy().generate_signals(_frame(close))
    assert (signals == 0.0).all()  # zero rate of change -> Coppock 0 -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=7)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5, dtype="float64")
    signals = CoppockCurveStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


def test_no_lookahead_truncation_invariant() -> None:
    rng = np.random.default_rng(3)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.5, dtype="float64")
    s = CoppockCurveStrategy(roc_long=14, roc_short=11, wma_window=10)
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
    signals = CoppockCurveStrategy(roc_long=14, roc_short=11, wma_window=10).generate_signals(
        _frame(close)
    )
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
