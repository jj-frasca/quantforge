"""ADXStrategy: param validation; Wilder directional movement — trade WITH the dominant direction
only when ADX confirms a strong trend; signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.adx import ADXStrategy


def _frame(close: pd.Series, span: float = 0.5) -> pd.DataFrame:
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
        ADXStrategy(window=1)


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        ADXStrategy(threshold=0.0)
    with pytest.raises(ValueError, match="threshold"):
        ADXStrategy(threshold=100.0)


def test_has_real_citation() -> None:
    assert any("Wilder" in c for c in ADXStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert ADXStrategy(window=14, threshold=25.0).parameters == {"window": 14, "threshold": 25.0}


def test_long_in_strong_uptrend() -> None:
    # A clean ramp: +DM dominates and ADX climbs well above the threshold -> long.
    close = pd.Series(np.linspace(50.0, 150.0, 120), name="close")
    signals = ADXStrategy(window=14, threshold=25.0).generate_signals(_frame(close))
    assert signals.iloc[-1] == 1.0


def test_short_in_strong_downtrend() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 120), name="close")
    signals = ADXStrategy(window=14, threshold=25.0).generate_signals(_frame(close))
    assert signals.iloc[-1] == -1.0


def test_flat_when_no_trend() -> None:
    # Constant price -> no directional movement -> ADX 0 -> below threshold -> flat.
    close = pd.Series(100.0, index=range(80), name="close")
    signals = ADXStrategy(window=14, threshold=25.0).generate_signals(_frame(close, span=0.0))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=23)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.4, name="close")
    signals = ADXStrategy().generate_signals(_frame(close))
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
    signals = ADXStrategy(window=14, threshold=25.0).generate_signals(_frame(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
