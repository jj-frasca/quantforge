"""DonchianATRTrailStrategy: param validation; Turtle-style N-bar-high breakout entry with a
Chandelier (ATR trailing-stop) exit; signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.donchian_atr_trail import DonchianATRTrailStrategy


def _ohlcv(close: pd.Series, spread: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_entry_window_below_two() -> None:
    with pytest.raises(ValueError, match="entry_window"):
        DonchianATRTrailStrategy(entry_window=1)


def test_rejects_atr_window_below_two() -> None:
    with pytest.raises(ValueError, match="atr_window"):
        DonchianATRTrailStrategy(atr_window=1)


def test_rejects_non_positive_atr_multiple() -> None:
    with pytest.raises(ValueError, match="atr_multiple"):
        DonchianATRTrailStrategy(atr_multiple=0.0)


def test_has_real_citation() -> None:
    assert any(
        "Turtle" in c or "LeBeau" in c for c in DonchianATRTrailStrategy().research_citations
    )


def test_parameters_round_trip() -> None:
    assert DonchianATRTrailStrategy(
        entry_window=20, atr_window=22, atr_multiple=3.0
    ).parameters == {
        "entry_window": 20,
        "atr_window": 22,
        "atr_multiple": 3.0,
    }


def test_long_on_sustained_uptrend() -> None:
    close = pd.Series(100.0 + np.arange(60), dtype="float64")
    signals = DonchianATRTrailStrategy(
        entry_window=20, atr_window=22, atr_multiple=3.0
    ).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 1.0


def test_short_on_sustained_downtrend() -> None:
    close = pd.Series(200.0 - np.arange(60), dtype="float64")
    signals = DonchianATRTrailStrategy(
        entry_window=20, atr_window=22, atr_multiple=3.0
    ).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == -1.0


def test_trailing_stop_exits_long_after_sharp_pullback() -> None:
    # 30 bars up (establish a long), then one bar drops far enough to trip the Chandelier
    # stop but NOT far enough to break the prior 20-bar low -> position goes flat, not short.
    up = 100.0 + np.arange(30)
    close = pd.Series(np.append(up, [120.0]), dtype="float64")
    signals = DonchianATRTrailStrategy(
        entry_window=20, atr_window=22, atr_multiple=3.0
    ).generate_signals(_ohlcv(close))
    assert signals.iloc[29] == 1.0
    assert signals.iloc[30] == 0.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(60))
    signals = DonchianATRTrailStrategy().generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=7)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5)
    signals = DonchianATRTrailStrategy().generate_signals(_ohlcv(close, spread=1.0))
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = DonchianATRTrailStrategy().generate_signals(_ohlcv(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
