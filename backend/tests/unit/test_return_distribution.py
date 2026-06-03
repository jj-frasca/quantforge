"""_return_distribution: histogram + skew + excess kurtosis on a return series.
Covers the defensive paths (empty input, zero-std degenerate series) that the
integration test doesn't reach."""

import numpy as np
import pandas as pd

from app.api.v1.backtest import _return_distribution


def test_empty_returns_yields_empty_distribution() -> None:
    dist = _return_distribution(pd.Series([], dtype=float), bins=10)
    assert dist.bins == []
    assert dist.skewness == 0.0
    assert dist.kurtosis == 0.0


def test_zero_std_returns_yields_zero_moments() -> None:
    # std == 0 path: an all-zeros series has mean=0 and std=0 exactly (no float drift),
    # so we hit the zero-std guard and skewness/kurtosis default to 0.
    dist = _return_distribution(pd.Series(np.zeros(100)), bins=10)
    assert sum(b.frequency for b in dist.bins) == 100
    assert dist.skewness == 0.0
    assert dist.kurtosis == 0.0


def test_gaussian_returns_have_near_zero_excess_kurtosis_and_skew() -> None:
    rng = np.random.default_rng(seed=42)
    series = pd.Series(rng.standard_normal(5000))
    dist = _return_distribution(series, bins=30)
    # Tolerances are loose — sample skew/kurt are noisy at N=5000
    assert abs(dist.skewness) < 0.2
    assert abs(dist.kurtosis) < 0.4
