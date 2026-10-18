"""ADR-319: regime alignment cannot reorder time or multiply observation identity."""

from typing import cast

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.regime_analysis import analyze_regimes


@pytest.mark.parametrize("side", ["strategy", "market"])
@pytest.mark.parametrize(
    "index",
    [
        pd.Index([3, 2, 1]),
        pd.Index([1, 3, 2, 4]),
        pd.Index([1, 1, 2]),
        pd.DatetimeIndex(["2020-01-01", "2020-01-03", "2020-01-02"]),
        pd.DatetimeIndex(["2020-01-01", "2020-01-01", "2020-01-02"]),
        pd.DatetimeIndex([pd.NaT]),
    ],
)
def test_either_invalid_original_calendar_refuses_before_alignment(
    side: str, index: pd.Index, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid = pd.Series([1.0] * len(index), index=index)
    valid = pd.Series([1.0, 1.01, 0.99], index=pd.RangeIndex(3))
    strategy, market = (invalid, valid) if side == "strategy" else (valid, invalid)

    def forbidden_align(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid original calendar reached alignment")

    monkeypatch.setattr(pd.Series, "align", forbidden_align)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(strategy, market, window=1)


@pytest.mark.parametrize("side", ["strategy", "market"])
def test_invalid_rows_cannot_disappear_in_intersection(side: str) -> None:
    duplicate = pd.Series([1.0, 1.01, 0.99], index=[0, 0, 2])
    valid = pd.Series([1.0, 1.02], index=[2, 3])
    strategy, market = (duplicate, valid) if side == "strategy" else (valid, duplicate)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(strategy, market, window=1)


def test_positive_horizon_future_calendar_witness_refuses() -> None:
    index = pd.to_datetime(["2021-01-01", "2021-01-03", "2021-01-02", "2021-01-04"])
    strategy = pd.Series([0.01, 0.03, -0.02, 0.04], index=index)
    market = pd.Series([100.0, 200.0, 100.0, 100.0], index=index)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(strategy, market, window=1)


def test_duplicate_cross_product_cannot_repeat_strategy_observations() -> None:
    strategy = pd.Series([0.1, -0.2, 0.3], index=[1, 1, 2])
    market = pd.Series([100.0, 120.0, 90.0, 95.0], index=[1, 1, 1, 2])
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(strategy, market, window=1)


@pytest.mark.parametrize("window", [-1, True, 1.0, None])
def test_original_horizon_guard_still_precedes_any_calendar_access(window: object) -> None:
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(cast(pd.Series, None), cast(pd.Series, None), window=cast(int, window))


@pytest.mark.parametrize(
    "index",
    [
        pd.RangeIndex(4),
        pd.Index([2, 4, 7, 9]),
        pd.Index(["a", "c", "d", "z"]),
        pd.date_range("2020-01-01", periods=4),
        pd.date_range("2020-01-01", periods=4, tz="UTC"),
        pd.date_range("2020-01-01", periods=4, tz="America/New_York"),
    ],
)
def test_ordered_index_families_preserve_values_and_sources(index: pd.Index) -> None:
    strategy = pd.Series([0.01, -0.02, 0.03, -0.01], index=index)
    market = pd.Series([100.0, 90.0, 110.0, 95.0], index=index)
    original_strategy, original_market = strategy.copy(deep=True), market.copy(deep=True)
    result = analyze_regimes(strategy, market, window=1)
    assert sum(item.n_bars for item in result.values()) == 4
    assert result["bear"].n_bars == 2
    assert result["bull"].n_bars == 2
    pd.testing.assert_series_equal(strategy, original_strategy)
    pd.testing.assert_series_equal(market, original_market)


@pytest.mark.parametrize("window", [0, 1, 20])
def test_ordered_empty_and_singleton_sources_retain_behavior(window: int) -> None:
    empty = pd.Series([], dtype=float)
    assert analyze_regimes(empty, empty, window=window) == {}
    result = analyze_regimes(pd.Series([0.1]), pd.Series([100.0]), window=window)
    assert set(result) == {"bull"}
    assert result["bull"].n_bars == 1
    assert result["bull"].total_return == pytest.approx(0.1)
    assert result["bull"].sharpe == 0.0


def test_disjoint_ordered_sources_keep_existing_empty_intersection() -> None:
    strategy = pd.Series([0.1, -0.2], index=[1, 2])
    market = pd.Series([100.0, 110.0], index=[3, 4])
    assert analyze_regimes(strategy, market, window=1) == {}


@given(
    labels=st.lists(st.integers(-100, 100), min_size=2, max_size=20, unique=True),
    rotation_seed=st.integers(1, 100),
    market_side=st.booleans(),
)
def test_rotated_original_order_is_rejected_on_either_source(
    labels: list[int], rotation_seed: int, market_side: bool
) -> None:
    labels = sorted(labels)
    offset = 1 + rotation_seed % (len(labels) - 1)
    rotated = labels[offset:] + labels[:offset]
    assert not pd.Index(rotated).is_monotonic_increasing
    valid = pd.Series([100.0] * len(labels), index=labels)
    invalid = pd.Series([100.0] * len(labels), index=rotated)
    strategy, market = (valid, invalid) if market_side else (invalid, valid)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(strategy, market, window=1)


@given(
    strategy_dates=st.lists(st.integers(0, 40), max_size=20, unique=True),
    market_dates=st.lists(st.integers(0, 40), max_size=20, unique=True),
    window=st.integers(0, 20),
)
def test_ordered_intersection_is_counted_exactly_once_without_source_mutation(
    strategy_dates: list[int], market_dates: list[int], window: int
) -> None:
    strategy = pd.Series([0.01] * len(strategy_dates), index=sorted(strategy_dates), dtype=float)
    market = pd.Series([100.0] * len(market_dates), index=sorted(market_dates), dtype=float)
    original_strategy, original_market = strategy.copy(deep=True), market.copy(deep=True)
    result = analyze_regimes(strategy, market, window=window)
    assert sum(item.n_bars for item in result.values()) == len(
        set(strategy_dates) & set(market_dates)
    )
    pd.testing.assert_series_equal(strategy, original_strategy)
    pd.testing.assert_series_equal(market, original_market)
