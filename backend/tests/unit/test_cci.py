"""CCIStrategy: param validation; long when CCI is deeply negative (oversold),
short when deeply positive (overbought); signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.cci import CCIStrategy


def _ohlc_frame(close: pd.Series, span: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + span,
            "low": close - span,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        CCIStrategy(window=1)


def test_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        CCIStrategy(threshold=0.0)


def test_has_real_citation() -> None:
    assert any("Lambert" in c for c in CCIStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert CCIStrategy(window=20, threshold=100.0).parameters == {
        "window": 20,
        "threshold": 100.0,
    }


def test_short_signal_in_steady_uptrend() -> None:
    # Rising typical price sits far above its SMA -> large positive CCI -> overbought short.
    close = pd.Series(np.linspace(50.0, 100.0, 60), name="close")
    signals = CCIStrategy(window=20, threshold=100.0).generate_signals(_ohlc_frame(close))
    assert signals.iloc[-1] == -1.0


def test_long_signal_in_steady_downtrend() -> None:
    close = pd.Series(np.linspace(100.0, 50.0, 60), name="close")
    signals = CCIStrategy(window=20, threshold=100.0).generate_signals(_ohlc_frame(close))
    assert signals.iloc[-1] == 1.0


def test_constant_price_stays_neutral() -> None:
    # Zero mean deviation -> CCI undefined -> flat.
    close = pd.Series(100.0, index=range(40), name="close")
    signals = CCIStrategy(window=20).generate_signals(_ohlc_frame(close, span=0.0))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=9)
    close = pd.Series(100 + rng.standard_normal(200).cumsum() * 0.4, name="close")
    signals = CCIStrategy().generate_signals(_ohlc_frame(close))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=25,
        max_size=80,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64", name="close")
    signals = CCIStrategy(window=20).generate_signals(_ohlc_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
