"""ADR-326: a published regime sign must agree with original price ordering."""

from dataclasses import asdict
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.regime_analysis import analyze_regimes
from app.validation.report import ValidationReport


def returns(n: int) -> pd.Series:
    return pd.Series(([0.01, -0.02, 0.03, 0.005] * (n // 4 + 1))[:n])


@pytest.mark.parametrize("dtype", ["int64", "uint64", "Int64", "UInt64"])
@pytest.mark.parametrize("window", [1, 7, 20, 39])
def test_native_integer_projection_cannot_publish_a_false_report(dtype: str, window: int) -> None:
    prices = pd.Series([2**60 - i for i in range(40)], dtype=dtype)
    original = prices.copy(deep=True)
    assert all(
        Fraction(int(prices.iloc[i]), int(prices.iloc[i - window])) < 1 for i in range(window, 40)
    )
    with pytest.raises(ValueError, match="native price order"):
        raw = analyze_regimes(returns(40), prices, window)
        ValidationReport(
            strategy_name="integer-order-witness",
            observed_sharpe=1.0,
            deflated_sharpe=0.5,
            pbo=0.1,
            parameter_stability_score=0.5,
            n_walk_forward_splits=0,
            n_purged_folds=0,
            regime_breakdown={label: asdict(metrics) for label, metrics in raw.items()},
        )
    pd.testing.assert_series_equal(prices, original)


@pytest.mark.parametrize("position", [1, 5])
def test_first_or_last_mature_mismatch_refuses_before_scoring(
    position: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = [2**60] * 6
    values[position] -= 1
    prices = pd.Series(values, dtype="int64")

    def forbidden(*args: object, **kwargs: object) -> float:
        pytest.fail("contradicted price order reached scoring")

    monkeypatch.setattr("app.validation.regime_analysis.sharpe_ratio", forbidden)
    with pytest.raises(ValueError, match="native price order"):
        analyze_regimes(returns(6), prices, 1)


@pytest.mark.parametrize("dtype", ["int64", "uint64", "Int64", "UInt64"])
@pytest.mark.parametrize("direction", [0, 1])
def test_large_flat_and_increasing_prices_remain_bull(dtype: str, direction: int) -> None:
    prices = pd.Series([2**60 + direction * i for i in range(40)], dtype=dtype)
    result = analyze_regimes(returns(40), prices, 20)
    assert set(result) == {"bull"}
    assert result["bull"].n_bars == 40


@pytest.mark.parametrize(
    "dtype", ["int64", "uint64", "Int64", "UInt64", "float32", "float64", "Float64", "float128"]
)
def test_supported_numeric_prices_preserve_exact_partition_and_sources(dtype: str) -> None:
    prices = pd.Series([100, 90, 110, 95, 105, 80], dtype=dtype, index=[2, 4, 7, 8, 11, 13])
    strategy = returns(6).set_axis(prices.index)
    original_prices, original_returns = prices.copy(deep=True), strategy.copy(deep=True)
    result = analyze_regimes(strategy, prices, 1)
    assert result["bear"].n_bars == result["bull"].n_bars == 3
    pd.testing.assert_series_equal(prices, original_prices)
    pd.testing.assert_series_equal(strategy, original_returns)


@pytest.mark.parametrize("window", [0, 6, 20])
def test_no_mature_rows_and_zero_horizon_keep_bull(window: int) -> None:
    prices = pd.Series([2**60 - i for i in range(6)], dtype="uint64")
    assert analyze_regimes(returns(6), prices, window)["bull"].n_bars == 6


def test_alignment_uses_only_matched_positions_and_keeps_disjoint_empty() -> None:
    prices = pd.Series([0, 100, 90, 110, 95, 0], index=[0, 2, 4, 7, 9, 11])
    strategy = returns(4).set_axis([2, 4, 7, 9])
    assert analyze_regimes(strategy, prices, 1)["bear"].n_bars == 2
    assert analyze_regimes(strategy.set_axis([20, 21, 22, 23]), prices, 1) == {}


@pytest.mark.parametrize("invalid", ["calendar", "wealth", "prices"])
def test_original_source_guards_precede_trailing_and_sign_check(
    invalid: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prices = pd.Series([2**60 - i for i in range(6)], dtype="int64")
    strategy = returns(6)
    if invalid == "calendar":
        prices.index = [0, 1, 1, 3, 4, 5]
    elif invalid == "wealth":
        strategy.iloc[0] = -1
    else:
        prices.iloc[0] = 0

    def forbidden(*args: object, **kwargs: object) -> pd.Series:
        pytest.fail("invalid source reached trailing arithmetic")

    monkeypatch.setattr(pd.Series, "pct_change", forbidden)
    with pytest.raises(
        ValueError,
        match={"calendar": "unique", "wealth": "above -1", "prices": "positive"}[invalid],
    ):
        analyze_regimes(strategy, prices, 1)


@given(
    dtype=st.sampled_from(["int64", "uint64", "Int64", "UInt64"]),
    offsets=st.lists(st.integers(0, 40), min_size=2, max_size=25),
    window=st.integers(1, 10),
    large=st.booleans(),
)
def test_native_integer_partition_agrees_with_independent_fraction_or_refuses(
    dtype: str, offsets: list[int], window: int, large: bool
) -> None:
    values = [(2**60 if large else 100) + i for i in offsets]
    prices = pd.Series(values, dtype=dtype)
    expected_bear = sum(
        Fraction(values[i], values[i - window]) < 1 for i in range(window, len(values))
    )
    if large and expected_bear:
        with pytest.raises(ValueError, match="native price order"):
            analyze_regimes(returns(len(values)), prices, window)
    else:
        result = analyze_regimes(returns(len(values)), prices, window)
        assert sum(item.n_bars for item in result.values()) == len(values)
        assert result["bear"].n_bars == expected_bear if expected_bear else "bear" not in result


def test_existing_trailing_exception_propagates_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> pd.Series:
        raise FloatingPointError("native trailing arithmetic")

    monkeypatch.setattr(pd.Series, "pct_change", broken)
    with pytest.raises(FloatingPointError, match="native trailing arithmetic"):
        analyze_regimes(returns(3), pd.Series([100, 99, 101]), 1)


def test_extended_native_precision_is_not_narrowed() -> None:
    high = np.longdouble("1e400")
    prices = pd.Series(np.array([high, high * 2, high], dtype=np.longdouble))
    result = analyze_regimes(returns(3), prices, 1)
    assert result["bear"].n_bars == 1 and result["bull"].n_bars == 2
