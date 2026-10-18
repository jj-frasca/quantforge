"""ADR-318: trailing-regime horizon identity precedes all price access."""

from dataclasses import asdict
from fractions import Fraction
from typing import cast
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

import app.validation.regime_analysis as module
from app.research.backtesting.metrics import sharpe_ratio
from app.validation.regime_analysis import analyze_regimes


@pytest.mark.parametrize(
    "window",
    [
        -1,
        -2,
        np.int64(-20),
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        0.0,
        1.0,
        -1.0,
        Fraction(1, 1),
        "2",
        None,
        1 + 0j,
        float("nan"),
        float("inf"),
        np.array(2),
        [2],
    ],
)
def test_invalid_window_refuses_before_alignment(window: object) -> None:
    class UnreadableReturns:
        def align(self, *args: object, **kwargs: object) -> None:
            pytest.fail("invalid original horizon reached alignment")

    with pytest.raises(ValueError, match=r"window.*nonnegative nonboolean integer"):
        analyze_regimes(
            cast(pd.Series, UnreadableReturns()),
            cast(pd.Series, None),
            window=cast(int, window),
        )


@pytest.mark.parametrize("window", [-1, -2, np.int64(-100)])
def test_negative_horizon_refuses_even_empty_sources(window: int) -> None:
    empty = pd.Series([], dtype=float)
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(empty, empty, window=window)


def test_negative_horizon_future_label_witness_refuses() -> None:
    index = pd.date_range("2020-01-01", periods=5, tz="UTC")
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02], index=index)
    market = pd.Series([100.0, 100.0, 100.0, 200.0, 100.0], index=index)
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(returns, market, window=-1)


@pytest.mark.parametrize("window", [np.int64(2), np.uint64(2), np.uint64(2**64 - 1)])
def test_integral_horizon_normalizes_before_pandas(
    window: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    returns = pd.Series([0.01, -0.02, 0.03])
    market = pd.Series([100.0, 99.0, 101.0])
    seen: list[int] = []

    def inspect_periods(self: pd.Series, periods: int) -> pd.Series:
        assert type(periods) is int
        assert periods == int(window)
        seen.append(periods)
        return pd.Series([0.0] * len(self), index=self.index)

    monkeypatch.setattr(pd.Series, "pct_change", inspect_periods)
    result = analyze_regimes(returns, market, window=window)
    assert seen == [int(window)]
    assert result["bull"].n_bars == len(returns)


@pytest.mark.parametrize("window", [0, np.int64(0), np.uint64(0)])
def test_zero_horizon_preserves_degenerate_all_bull(window: int) -> None:
    returns = pd.Series([0.01, -0.02, 0.03, -0.01])
    market = pd.Series([100.0, 80.0, 120.0, 70.0])
    result = analyze_regimes(returns, market, window=window)
    assert set(result) == {"bull"}
    assert result["bull"].n_bars == len(returns)
    assert result["bull"].total_return == float((1 + returns).prod() - 1)
    assert result["bull"].sharpe == sharpe_ratio(returns)


def test_default_horizon_equals_explicit_twenty() -> None:
    market = pd.Series([100.0 + i for i in range(40)])
    returns = market.pct_change().fillna(0.0)
    implicit = analyze_regimes(returns, market)
    explicit = analyze_regimes(returns, market, window=20)
    assert {k: asdict(v) for k, v in implicit.items()} == {
        k: asdict(v) for k, v in explicit.items()
    }


def _memberships(returns: pd.Series, market: pd.Series, window: int) -> dict[int, str]:
    """Observe actual original row identities supplied to each regime's metric."""
    groups: list[list[int]] = []

    def observe(group: pd.Series) -> float:
        groups.append(list(group.index))
        return sharpe_ratio(group)

    with patch.object(module, "sharpe_ratio", observe):
        result = analyze_regimes(returns, market, window=window)
    return {
        index: label for label, members in zip(result, groups, strict=True) for index in members
    }


@given(
    prices=st.lists(st.integers(50, 200), min_size=8, max_size=30),
    window=st.integers(0, 10),
    cutoff_seed=st.integers(1, 100),
)
def test_supported_horizons_keep_prior_labels_under_future_price_changes(
    prices: list[int], window: int, cutoff_seed: int
) -> None:
    cutoff = 1 + cutoff_seed % (len(prices) - 1)
    market = pd.Series(prices, dtype=float)
    returns = pd.Series([0.01 if i % 2 else -0.02 for i in range(len(prices))])
    changed = market.copy()
    changed.iloc[cutoff:] *= 1.5
    original_labels = _memberships(returns, market, window)
    future_changed_labels = _memberships(returns, changed, window)
    prefix_labels = _memberships(returns.iloc[:cutoff], market.iloc[:cutoff], window)
    for index in range(cutoff):
        assert original_labels[index] == future_changed_labels[index] == prefix_labels[index]
    assert len(original_labels) == len(returns)


@given(window=st.integers(min_value=-(10**30), max_value=-1))
def test_no_negative_integral_horizon_reaches_data(window: int) -> None:
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(cast(pd.Series, None), cast(pd.Series, None), window=window)
