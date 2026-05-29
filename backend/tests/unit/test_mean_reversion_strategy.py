"""MeanReversionStrategy: real citation, param validation, shorts a price spike above the rolling mean; Hypothesis invariant that signals stay in [-1,1]."""

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.mean_reversion import MeanReversionStrategy


def _frame(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame({"close": closes}, index=index)


def test_mean_reversion_has_real_citation() -> None:
    assert any("Avellaneda" in c for c in MeanReversionStrategy().research_citations)


def test_mean_reversion_parameters_round_trip() -> None:
    assert MeanReversionStrategy(window=20, k=2.0).parameters == {"window": 20, "k": 2.0}


def test_mean_reversion_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match="window"):
        MeanReversionStrategy(window=1)
    with pytest.raises(ValueError, match="k"):
        MeanReversionStrategy(k=0.0)


def test_spike_above_mean_produces_short_signal() -> None:
    frame = _frame([100.0] * 10 + [130.0])  # sudden jump above the rolling mean
    signals = MeanReversionStrategy(window=5, k=2.0).generate_signals(frame)
    assert signals.iloc[-1] < 0.0  # rich price -> short (mean reversion)


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=80,
    )
)
def test_mean_reversion_signals_in_range(closes: list[float]) -> None:
    frame = _frame(closes)
    signals = MeanReversionStrategy(window=5, k=2.0).generate_signals(frame)
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(frame.index)
