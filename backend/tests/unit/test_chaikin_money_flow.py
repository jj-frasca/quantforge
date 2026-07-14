"""ChaikinMoneyFlowStrategy: param validation; volume-weighted accumulation/distribution (long on
net buying pressure, short on net selling pressure); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.chaikin_money_flow import ChaikinMoneyFlowStrategy


def _frame(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: float = 1_000_000.0
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": pd.Series(volume, index=close.index),
        },
        index=close.index,
    )


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        ChaikinMoneyFlowStrategy(window=1)


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        ChaikinMoneyFlowStrategy(threshold=0.0)


def test_has_real_citation() -> None:
    assert any("Chaikin" in c for c in ChaikinMoneyFlowStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ChaikinMoneyFlowStrategy(window=20, threshold=0.05).parameters == {
        "window": 20,
        "threshold": 0.05,
    }


def test_long_when_closes_pin_to_the_high() -> None:
    # close == high every bar -> money-flow multiplier = +1 -> CMF = 1 -> strong buying -> long.
    n = 40
    idx = pd.RangeIndex(n)
    high = pd.Series(101.0, index=idx)
    low = pd.Series(99.0, index=idx)
    close = high.copy()
    signals = ChaikinMoneyFlowStrategy(window=20).generate_signals(_frame(high, low, close))
    assert signals.iloc[-1] == 1.0


def test_short_when_closes_pin_to_the_low() -> None:
    n = 40
    idx = pd.RangeIndex(n)
    high = pd.Series(101.0, index=idx)
    low = pd.Series(99.0, index=idx)
    close = low.copy()
    signals = ChaikinMoneyFlowStrategy(window=20).generate_signals(_frame(high, low, close))
    assert signals.iloc[-1] == -1.0


def test_flat_bar_contributes_no_money_flow() -> None:
    # high == low every bar -> multiplier undefined -> treated as zero -> CMF 0 -> flat.
    idx = pd.RangeIndex(40)
    price = pd.Series(100.0, index=idx)
    signals = ChaikinMoneyFlowStrategy(window=20).generate_signals(_frame(price, price, price))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=17)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4)
    signals = ChaikinMoneyFlowStrategy().generate_signals(_frame(close + 0.5, close - 0.5, close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=21,
        max_size=100,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = ChaikinMoneyFlowStrategy(window=20).generate_signals(
        _frame(close + 0.5, close - 0.5, close)
    )
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
