"""VolManagedMomentumStrategy: param validation; a trailing-return momentum sign scaled
by inverse realized VARIANCE (Moreira & Muir 2017); position is continuous in [-1, 1];
warmup is flat; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.vol_managed_momentum import VolManagedMomentumStrategy


def _close_frame(close: pd.Series) -> pd.DataFrame:
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


def test_rejects_non_positive_lookback() -> None:
    with pytest.raises(ValueError, match="lookback"):
        VolManagedMomentumStrategy(lookback=0)


def test_rejects_invalid_vol_window() -> None:
    with pytest.raises(ValueError, match="vol_window"):
        VolManagedMomentumStrategy(vol_window=1)


def test_rejects_non_positive_target_vol() -> None:
    with pytest.raises(ValueError, match="target_vol"):
        VolManagedMomentumStrategy(target_vol=0.0)


def test_has_real_citation() -> None:
    assert any("Moreira" in c for c in VolManagedMomentumStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert VolManagedMomentumStrategy(lookback=60, vol_window=20, target_vol=0.15).parameters == {
        "lookback": 60,
        "vol_window": 20,
        "target_vol": 0.15,
    }


def test_full_long_in_smooth_uptrend() -> None:
    # Smooth uptrend: momentum sign is +1 and realized variance is tiny, so the
    # inverse-variance scale clips to 1 -> position is exactly +1.
    close = pd.Series(np.linspace(50.0, 150.0, 200))
    positions = VolManagedMomentumStrategy(
        lookback=20, vol_window=20, target_vol=0.20
    ).generate_signals(_close_frame(close))
    assert positions.iloc[-1] == pytest.approx(1.0)


def test_full_short_in_smooth_downtrend() -> None:
    close = pd.Series(np.linspace(150.0, 50.0, 200))
    positions = VolManagedMomentumStrategy(
        lookback=20, vol_window=20, target_vol=0.20
    ).generate_signals(_close_frame(close))
    assert positions.iloc[-1] == pytest.approx(-1.0)


def test_position_shrinks_when_variance_exceeds_target() -> None:
    rng = np.random.default_rng(seed=11)
    drift = np.linspace(0.0, 60.0, 240)
    noise = rng.standard_normal(240) * 6.0
    close = pd.Series(100.0 + drift + noise)
    positions = VolManagedMomentumStrategy(
        lookback=20, vol_window=20, target_vol=0.05
    ).generate_signals(_close_frame(close))
    tail = positions.iloc[-20:]
    assert (tail.abs() < 1.0).all()
    assert (tail.abs() > 0.0).any()


def test_flat_when_price_is_constant() -> None:
    close = pd.Series(100.0, index=pd.RangeIndex(120))
    positions = VolManagedMomentumStrategy().generate_signals(_close_frame(close))
    assert (positions == 0.0).all()


def test_warmup_is_flat() -> None:
    close = pd.Series(np.linspace(50.0, 150.0, 200))
    positions = VolManagedMomentumStrategy(lookback=30, vol_window=20).generate_signals(
        _close_frame(close)
    )
    assert positions.iloc[0] == 0.0
    assert positions.iloc[5] == 0.0


@given(
    closes=st.lists(
        st.floats(min_value=2.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=40,
        max_size=120,
    )
)
def test_positions_in_range_and_indexed(closes: list[float]) -> None:
    close = pd.Series(closes, dtype="float64")
    positions = VolManagedMomentumStrategy(lookback=10, vol_window=10).generate_signals(
        _close_frame(close)
    )
    assert positions.between(-1.0, 1.0).all()
    assert positions.index.equals(close.index)
