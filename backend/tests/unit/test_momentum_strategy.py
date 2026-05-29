"""MomentumStrategy: real citation, param validation, long in an uptrend, flat warmup; Hypothesis invariant that signals stay in [-1,1]."""

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame
from app.research.strategies.momentum import MomentumStrategy


def test_momentum_has_real_citation() -> None:
    assert any("Jegadeesh" in c for c in MomentumStrategy().research_citations)


def test_momentum_parameters_round_trip() -> None:
    assert MomentumStrategy(lookback=60, skip=5).parameters == {"lookback": 60, "skip": 5}


def test_momentum_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match="lookback"):
        MomentumStrategy(lookback=0)
    with pytest.raises(ValueError, match="skip"):
        MomentumStrategy(skip=-1)


def test_momentum_uptrend_goes_long() -> None:
    frame = bars_to_frame(builders.clean_series(n=80))  # steady uptrend
    signals = MomentumStrategy(lookback=20, skip=2).generate_signals(frame)
    assert signals.index.equals(frame.index)
    assert signals.iloc[0] == 0.0  # warmup
    assert signals.iloc[-1] == 1.0


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=15,
        max_size=80,
    )
)
def test_momentum_signals_in_range(closes: list[float]) -> None:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    frame = pd.DataFrame({"close": closes}, index=index)
    signals = MomentumStrategy(lookback=5, skip=1).generate_signals(frame)
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(frame.index)
