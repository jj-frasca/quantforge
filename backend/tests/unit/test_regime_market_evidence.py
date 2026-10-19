"""ADR-323: a bull/bear partition requires actual matched market-price evidence."""

from dataclasses import asdict
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.regime_analysis import analyze_regimes
from app.validation.report import ValidationReport


@pytest.mark.parametrize("invalid", [np.nan, 0.0, True])
def test_actual_report_fabricated_bull_witness_refuses(invalid: object) -> None:
    returns = pd.Series([0.01, -0.02, 0.03] * 8)
    with pytest.raises(ValueError, match="matched regime prices"):
        raw = analyze_regimes(returns, pd.Series(invalid, index=returns.index))
        # Before the guard this real model accepted all three fabricated claims.
        ValidationReport(
            strategy_name="witness",
            observed_sharpe=1.0,
            deflated_sharpe=0.5,
            pbo=0.1,
            parameter_stability_score=0.5,
            n_walk_forward_splits=0,
            n_purged_folds=0,
            regime_breakdown={label: asdict(metrics) for label, metrics in raw.items()},
        )


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, 0.0, -100.0])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_invalid_matched_price_refuses_before_market_math(
    invalid: float, position: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    prices = pd.Series([100.0, 101.0, 99.0])
    prices.iloc[position] = invalid

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid market prices reached pct_change")

    monkeypatch.setattr(pd.Series, "pct_change", forbidden)
    with pytest.raises(ValueError, match=r"matched regime prices.*positive.*finite"):
        analyze_regimes(pd.Series([0.01, -0.02, 0.03]), prices, window=1)


@pytest.mark.parametrize(
    "prices",
    [
        pd.Series([True, False]),
        pd.Series([True, True], dtype="boolean"),
        pd.Series([100 + 1j, 101 + 2j]),
        pd.Series(["100", "101"]),
        pd.Series([100.0, 101.0], dtype=object),
        pd.Series([Decimal("100"), Decimal("101")]),
        pd.Series(pd.date_range("2020-01-01", periods=2)),
    ],
)
def test_unsupported_matched_price_dtype_refuses_before_market_math(
    prices: pd.Series, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("unsupported price dtype reached pct_change")

    monkeypatch.setattr(pd.Series, "pct_change", forbidden)
    with pytest.raises(ValueError, match=r"matched regime prices.*real nonboolean numeric"):
        analyze_regimes(pd.Series([0.01, -0.02]), prices, window=0)


@pytest.mark.parametrize("dtype", ["Float64", "Int64"])
def test_nullable_missing_price_refuses_even_at_zero_horizon(dtype: str) -> None:
    with pytest.raises(ValueError, match=r"matched regime prices.*positive.*finite"):
        analyze_regimes(pd.Series([0.01, -0.02]), pd.Series([100, pd.NA], dtype=dtype), window=0)


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -1.0, 0.0])
def test_invalid_numeric_prices_outside_intersection_remain_unscored(invalid: float) -> None:
    returns = pd.Series([0.01, -0.02], index=[1, 2])
    market = pd.Series([invalid, 100.0, 101.0, invalid], index=[0, 1, 2, 3])
    actual = analyze_regimes(returns, market, window=1)
    expected = analyze_regimes(returns, market.loc[[1, 2]], window=1)
    assert actual == expected
    assert actual["bull"].n_bars == 2


def test_empty_and_disjoint_unsupported_prices_retain_empty_results() -> None:
    empty = pd.Series([], dtype=object)
    assert analyze_regimes(pd.Series([], dtype=float), empty) == {}
    assert analyze_regimes(pd.Series([0.01], index=[0]), pd.Series(["bad"], index=[1])) == {}


def test_count_calendar_and_wealth_precedence_stays_before_market_values() -> None:
    returns = pd.Series([-3.0, 0.01], index=[1, 0])
    market = pd.Series([0.0, np.nan], index=[1, 0])
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(returns, market, window=-1)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(returns, market, window=1)
    with pytest.raises(ValueError, match="above -1"):
        analyze_regimes(returns.sort_index(), market.sort_index(), window=1)


@pytest.mark.parametrize("dtype", ["int64", "uint64", "float32", "float64", "Float64", "Int64"])
def test_valid_numeric_prices_preserve_partition_and_source(dtype: str) -> None:
    returns = pd.Series([0.01, -0.02, 0.03, -0.01])
    market = pd.Series([100, 110, 99, 105], dtype=dtype)
    before = market.copy(deep=True)
    result = analyze_regimes(returns, market, window=1)
    assert result["bull"].n_bars == 3
    assert result["bear"].n_bars == 1
    assert result["bear"].total_return == 1.03 - 1
    pd.testing.assert_series_equal(market, before)
    assert analyze_regimes(returns, market, window=0)["bull"].n_bars == 4


def test_native_finite_prices_outside_binary64_range_remain_supported() -> None:
    value = np.longdouble("1e400")
    assert np.isfinite(value) and value > np.finfo(np.float64).max
    market = pd.Series(np.array([value, value * 2, value], dtype=np.longdouble))
    before = market.copy(deep=True)
    result = analyze_regimes(pd.Series([0.01, -0.02, 0.03]), market, window=1)
    assert result["bull"].n_bars == 2 and result["bear"].n_bars == 1
    pd.testing.assert_series_equal(market, before)


@given(
    prices=st.lists(st.integers(1, 10000), min_size=2, max_size=30),
    window=st.integers(0, 10),
)
def test_valid_positive_prices_partition_matched_returns_once(
    prices: list[int], window: int
) -> None:
    market = pd.Series(prices, dtype=float)
    returns = pd.Series([0.01, -0.02, 0.03] * (len(prices) // 3 + 1)).iloc[: len(prices)]
    result = analyze_regimes(returns, market, window=window)
    bear = sum(i >= window and prices[i] < prices[i - window] for i in range(len(prices)))
    if bear:
        assert result["bear"].n_bars == bear
    else:
        assert "bear" not in result
    assert sum(group.n_bars for group in result.values()) == len(prices)


@given(
    position=st.integers(0, 5),
    invalid=st.one_of(
        st.floats(max_value=0, allow_nan=False, allow_infinity=False),
        st.sampled_from([np.nan, np.inf, -np.inf]),
    ),
    window=st.integers(0, 10),
)
def test_any_invalid_matched_price_refuses_without_source_or_policy_mutation(
    position: int, invalid: float, window: int
) -> None:
    market = pd.Series([100.0] * 6)
    market.iloc[position] = invalid
    before = market.copy(deep=True)
    policy = np.geterr().copy()
    with pytest.raises(ValueError, match="matched regime prices"):
        analyze_regimes(pd.Series([0.01, -0.02] * 3), market, window=window)
    pd.testing.assert_series_equal(market, before)
    assert np.geterr() == policy
