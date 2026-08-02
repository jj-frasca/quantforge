"""SqueezeBreakoutStrategy: param validation; John Carter's TTM squeeze (Bollinger Bands
compressing inside Keltner Channels) that fires a directional breakout on expansion; signals in
{-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.squeeze_breakout import SqueezeBreakoutStrategy


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


def _squeeze_then_move(direction: float, n_flat: int = 40, n_move: int = 30) -> pd.DataFrame:
    flat = np.full(n_flat, 100.0)
    move = 100.0 + direction * 3.0 * (np.arange(n_move) + 1)
    return _ohlcv(pd.Series(np.concatenate([flat, move]), dtype="float64"))


def test_rejects_window_below_two() -> None:
    with pytest.raises(ValueError, match="window"):
        SqueezeBreakoutStrategy(window=1)


def test_rejects_non_positive_bb_num_std() -> None:
    with pytest.raises(ValueError, match="bb_num_std"):
        SqueezeBreakoutStrategy(bb_num_std=0.0)


def test_rejects_non_positive_kc_multiple() -> None:
    with pytest.raises(ValueError, match="kc_multiple"):
        SqueezeBreakoutStrategy(kc_multiple=0.0)


def test_has_real_citation() -> None:
    assert any("Carter" in c for c in SqueezeBreakoutStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert SqueezeBreakoutStrategy(window=20, bb_num_std=2.0, kc_multiple=1.5).parameters == {
        "window": 20,
        "bb_num_std": 2.0,
        "kc_multiple": 1.5,
    }


def test_long_when_squeeze_fires_upward() -> None:
    signals = SqueezeBreakoutStrategy().generate_signals(_squeeze_then_move(1.0))
    assert signals.iloc[-1] == 1.0


def test_short_when_squeeze_fires_downward() -> None:
    signals = SqueezeBreakoutStrategy().generate_signals(_squeeze_then_move(-1.0))
    assert signals.iloc[-1] == -1.0


def test_flat_during_compression() -> None:
    # A steady low-volatility band keeps Bollinger inside Keltner -> squeeze stays on -> flat.
    df = _ohlcv(pd.Series(100.0, index=pd.RangeIndex(60)))
    signals = SqueezeBreakoutStrategy().generate_signals(df)
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=11)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.6)
    signals = SqueezeBreakoutStrategy().generate_signals(_ohlcv(close, spread=1.0))
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
    signals = SqueezeBreakoutStrategy().generate_signals(_ohlcv(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
