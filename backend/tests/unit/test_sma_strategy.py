import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame
from app.research.strategies.base import BaseStrategy
from app.research.strategies.sma import SMAStrategy


def test_base_strategy_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseStrategy()  # type: ignore[abstract]


def test_sma_has_non_empty_research_citations() -> None:
    assert SMAStrategy().research_citations


def test_sma_rejects_fast_not_less_than_slow() -> None:
    with pytest.raises(ValueError, match="fast"):
        SMAStrategy(fast=50, slow=20)


def test_sma_rejects_fast_below_one() -> None:
    with pytest.raises(ValueError, match="fast"):
        SMAStrategy(fast=0, slow=10)


def test_sma_parameters_round_trip() -> None:
    assert SMAStrategy(fast=5, slow=10).parameters == {"fast": 5, "slow": 10}


def test_sma_signals_index_matches_and_in_range() -> None:
    frame = bars_to_frame(builders.clean_series(n=40))
    signals = SMAStrategy(fast=5, slow=10).generate_signals(frame)
    assert signals.index.equals(frame.index)
    assert signals.between(-1.0, 1.0).all()


def test_sma_warmup_is_flat_and_uptrend_is_long() -> None:
    frame = bars_to_frame(builders.clean_series(n=40))  # steady uptrend
    signals = SMAStrategy(fast=5, slow=10).generate_signals(frame)
    assert signals.iloc[0] == 0.0  # warmup before slow window fills
    assert signals.iloc[-1] == 1.0  # fast MA above slow MA in an uptrend


@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=12,
        max_size=60,
    )
)
def test_sma_signals_always_in_range(closes: list[float]) -> None:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    frame = pd.DataFrame({"close": closes}, index=index)
    signals = SMAStrategy(fast=3, slow=8).generate_signals(frame)
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(frame.index)
