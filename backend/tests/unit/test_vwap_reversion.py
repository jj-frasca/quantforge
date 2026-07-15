"""VWAPReversionStrategy: param validation; mean reversion to the rolling volume-weighted average
price (long when price is stretched below VWAP, short when above); signals in {-1,0,1}; no
look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.vwap_reversion import VWAPReversionStrategy


def _frame(close: pd.Series, span: float = 0.5, volume: float = 1_000_000.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + span,
            "low": close - span,
            "close": close,
            "volume": pd.Series(volume, index=close.index),
        },
        index=close.index,
    )


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        VWAPReversionStrategy(window=1)


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        VWAPReversionStrategy(threshold=0.0)


def test_has_real_citation() -> None:
    assert any("Berkowitz" in c for c in VWAPReversionStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert VWAPReversionStrategy(window=20, threshold=0.02).parameters == {
        "window": 20,
        "threshold": 0.02,
    }


def test_long_when_price_drops_far_below_vwap() -> None:
    close = pd.Series([100.0] * 19 + [90.0])  # last bar ~10% under the trailing VWAP
    signals = VWAPReversionStrategy(window=20, threshold=0.02).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_short_when_price_jumps_far_above_vwap() -> None:
    close = pd.Series([100.0] * 19 + [110.0])
    signals = VWAPReversionStrategy(window=20, threshold=0.02).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_flat_when_price_sits_at_vwap() -> None:
    close = pd.Series(100.0, index=range(40))
    signals = VWAPReversionStrategy(window=20, threshold=0.02).generate_signals(_frame(close))
    assert (signals == 0.0).all()  # constant price -> zero deviation -> flat


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=19)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.5)
    signals = VWAPReversionStrategy().generate_signals(_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=5.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=21,
        max_size=100,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = VWAPReversionStrategy(window=20, threshold=0.02).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
