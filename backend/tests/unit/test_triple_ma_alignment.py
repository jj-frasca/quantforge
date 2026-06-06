"""TripleMAAlignmentStrategy: param validation; long only when fast > medium > slow;
short only when fast < medium < slow; flat otherwise; warmup is flat; no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.triple_ma_alignment import TripleMAAlignmentStrategy


def test_rejects_fast_less_than_one() -> None:
    with pytest.raises(ValueError, match="fast window must be >= 1"):
        TripleMAAlignmentStrategy(fast=0, medium=20, slow=50)


def test_rejects_medium_not_greater_than_fast() -> None:
    with pytest.raises(ValueError, match="medium window must be > fast"):
        TripleMAAlignmentStrategy(fast=20, medium=20, slow=50)


def test_rejects_slow_not_greater_than_medium() -> None:
    with pytest.raises(ValueError, match="slow window must be > medium"):
        TripleMAAlignmentStrategy(fast=10, medium=30, slow=30)


def test_long_signal_in_sustained_uptrend() -> None:
    # A clean linear uptrend: fast > medium > slow at every bar past warmup.
    series = pd.Series(np.linspace(50, 200, 300), name="close")
    data = pd.DataFrame({"close": series})
    signals = TripleMAAlignmentStrategy(fast=10, medium=30, slow=100).generate_signals(data)
    assert signals.iloc[-1] == 1.0


def test_short_signal_in_sustained_downtrend() -> None:
    series = pd.Series(np.linspace(200, 50, 300), name="close")
    data = pd.DataFrame({"close": series})
    signals = TripleMAAlignmentStrategy(fast=10, medium=30, slow=100).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_chop_yields_substantial_flat_share() -> None:
    # A no-drift random walk produces occasional aligned patches by chance but no
    # sustained trend. The flat share past warmup should still be meaningfully large —
    # strict three-way agreement is harder to hit than a two-MA crossover. We don't
    # over-tune the threshold: ~30% flat is enough to demonstrate the principle without
    # encoding luck in the seed.
    rng = np.random.default_rng(seed=11)
    series = pd.Series(100 + rng.standard_normal(300) * 0.5, name="close")
    data = pd.DataFrame({"close": series})
    signals = TripleMAAlignmentStrategy(fast=10, medium=30, slow=100).generate_signals(data)
    tail = signals.iloc[100:]
    flat_share = (tail == 0.0).mean()
    assert flat_share > 0.3, f"expected substantial flat share in chop, got flat_share={flat_share}"


def test_warmup_region_is_flat() -> None:
    series = pd.Series(np.linspace(50, 200, 300), name="close")
    data = pd.DataFrame({"close": series})
    signals = TripleMAAlignmentStrategy(fast=10, medium=30, slow=100).generate_signals(data)
    # Before the slow window fills, the comparisons are NaN -> filled to False -> flat.
    assert signals.iloc[0] == 0.0
    assert signals.iloc[50] == 0.0  # past fast/medium but not slow


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=4)
    series = pd.Series(100 + rng.standard_normal(400).cumsum() * 0.3, name="close")
    data = pd.DataFrame({"close": series})
    signals = TripleMAAlignmentStrategy().generate_signals(data)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})
