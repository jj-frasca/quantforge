"""VolTargetedSMAStrategy: param validation; direction follows SMA crossover; position
size is inversely scaled by realized vol and never exceeds 1 (no leverage); positions
stay in the §8-invariant [-1, 1] range; warmup region is flat."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.vol_targeted_sma import VolTargetedSMAStrategy


def test_rejects_fast_less_than_one() -> None:
    with pytest.raises(ValueError, match="fast window must be >= 1"):
        VolTargetedSMAStrategy(fast=0, slow=20)


def test_rejects_fast_not_less_than_slow() -> None:
    with pytest.raises(ValueError, match="fast window must be < slow"):
        VolTargetedSMAStrategy(fast=50, slow=20)


def test_rejects_invalid_vol_window() -> None:
    with pytest.raises(ValueError, match="vol_window"):
        VolTargetedSMAStrategy(vol_window=1)


def test_rejects_non_positive_target_vol() -> None:
    with pytest.raises(ValueError, match="target_vol"):
        VolTargetedSMAStrategy(target_vol=0)


def test_direction_matches_sma_crossover_in_low_vol() -> None:
    # In a smooth uptrend the SMA crossover signal is +1; realized vol is tiny so the
    # scale clips to 1 and the position should be exactly +1.
    series = pd.Series(np.linspace(50, 150, 200), name="close")
    data = pd.DataFrame({"close": series})
    positions = VolTargetedSMAStrategy(
        fast=10, slow=30, vol_window=20, target_vol=0.20
    ).generate_signals(data)
    assert positions.iloc[-1] == pytest.approx(1.0)


def test_position_shrinks_when_realized_vol_exceeds_target() -> None:
    # Noisy uptrend: SMA direction is still +1 but realized vol is high; clip to <= 1
    # means the position should be strictly less than 1 in absolute value.
    rng = np.random.default_rng(seed=5)
    drift = np.linspace(0, 50, 200)
    noise = rng.standard_normal(200) * 5.0  # large noise -> high realized vol
    series = pd.Series(100 + drift + noise, name="close")
    data = pd.DataFrame({"close": series})
    positions = VolTargetedSMAStrategy(
        fast=10, slow=30, vol_window=20, target_vol=0.05
    ).generate_signals(data)
    # Look at the tail (past warmup), where vol estimate is settled
    assert (positions.iloc[-20:].abs() < 1.0).all()
    assert (positions.iloc[-20:].abs() > 0.0).any()


def test_positions_are_always_in_minus_one_to_one() -> None:
    rng = np.random.default_rng(seed=7)
    series = pd.Series(100 + rng.standard_normal(400).cumsum() * 0.5, name="close")
    data = pd.DataFrame({"close": series})
    positions = VolTargetedSMAStrategy().generate_signals(data)
    assert positions.between(-1.0, 1.0).all()


def test_warmup_period_is_flat() -> None:
    series = pd.Series(np.linspace(50, 150, 200), name="close")
    data = pd.DataFrame({"close": series})
    positions = VolTargetedSMAStrategy(fast=10, slow=30, vol_window=20).generate_signals(data)
    # Before the SLOW window fills, direction is 0; before the vol window fills, scale is 0.
    # Either way the earliest bars must be 0.
    assert positions.iloc[0] == 0.0
    assert positions.iloc[5] == 0.0
