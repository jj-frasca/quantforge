"""DualMomentumStrategy: param validation; Antonacci's absolute+relative dual momentum as a
single-name long/flat rule (long only when the trailing return is positive AND price is above
its own longer trend); signals in {0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.dual_momentum import DualMomentumStrategy


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": pd.Series(1_000_000.0, index=close.index),
        },
        index=close.index,
    )


def test_rejects_lookback_below_one() -> None:
    with pytest.raises(ValueError, match="lookback"):
        DualMomentumStrategy(lookback=0)


def test_rejects_trend_window_below_two() -> None:
    with pytest.raises(ValueError, match="trend_window"):
        DualMomentumStrategy(trend_window=1)


def test_has_real_citation() -> None:
    assert any("Antonacci" in c for c in DualMomentumStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert DualMomentumStrategy(lookback=120, trend_window=200).parameters == {
        "lookback": 120,
        "trend_window": 200,
    }


def test_long_when_trend_and_absolute_momentum_agree() -> None:
    close = pd.Series(100.0 + np.arange(60), dtype="float64")
    signals = DualMomentumStrategy(lookback=10, trend_window=20).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 1.0


def test_flat_on_sustained_downtrend() -> None:
    # Absolute momentum negative -> never long, regardless of the trend filter.
    close = pd.Series(200.0 - np.arange(60), dtype="float64")
    signals = DualMomentumStrategy(lookback=10, trend_window=20).generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_flat_when_recovering_but_still_below_longer_trend() -> None:
    # V-shape: absolute momentum (10-bar) is POSITIVE off the bottom, but price is still
    # below its 40-bar trend -> the relative-momentum gate keeps it flat. This is the whole
    # point of dual momentum: BOTH gates must pass.
    plateau = np.full(20, 150.0)
    down = np.linspace(150.0, 100.0, 10)
    up = np.linspace(100.0, 120.0, 10)
    close = pd.Series(np.concatenate([plateau, down, up]), dtype="float64")
    signals = DualMomentumStrategy(lookback=10, trend_window=40).generate_signals(_ohlcv(close))
    assert signals.iloc[-1] == 0.0


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(60))
    signals = DualMomentumStrategy(lookback=10, trend_window=20).generate_signals(_ohlcv(close))
    assert (signals == 0.0).all()


def test_signal_values_are_long_or_flat_only() -> None:
    rng = np.random.default_rng(seed=17)
    close = pd.Series(100 + rng.standard_normal(300).cumsum() * 0.5)
    signals = DualMomentumStrategy().generate_signals(_ohlcv(close))
    assert set(signals.unique()).issubset({0.0, 1.0})


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=30,
        max_size=120,
    )
)
def test_signals_in_range(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    signals = DualMomentumStrategy(lookback=10, trend_window=20).generate_signals(_ohlcv(close))
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(close.index)
