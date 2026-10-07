"""BenchmarkComparator: SPY-vs-SPY is neutral (excess≈0, IR≈0, alpha≈0, beta≈1), excess captures constant outperformance, 2x leverage → beta 2 / alpha 0, constant benchmark is division-safe."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator


def _returns(seed: int = 42, n: int = 252) -> pd.Series:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(rng.normal(0.0005, 0.01, n), index=index)


def test_spy_vs_spy_baseline_is_neutral() -> None:
    bench = _returns()
    comparison = BenchmarkComparator().compare(bench, bench)
    assert comparison.information_ratio == pytest.approx(0.0, abs=1e-9)
    assert comparison.alpha == pytest.approx(0.0, abs=1e-9)
    assert comparison.beta == pytest.approx(1.0, abs=1e-9)
    assert comparison.tracking_error == pytest.approx(0.0, abs=1e-9)
    assert comparison.benchmark_relative_drawdown == pytest.approx(0.0, abs=1e-12)


def test_constant_outperformance_shows_in_excess_returns() -> None:
    bench = _returns()
    strat = bench + 0.001
    comparison = BenchmarkComparator().compare(strat, bench)
    assert comparison.excess_returns.mean() == pytest.approx(0.001, abs=1e-9)
    assert comparison.beta == pytest.approx(1.0, abs=1e-9)  # parallel shift, same slope


def test_leveraged_strategy_has_double_beta_and_zero_alpha() -> None:
    bench = _returns()
    comparison = BenchmarkComparator().compare(2.0 * bench, bench)
    assert comparison.beta == pytest.approx(2.0, abs=1e-9)
    assert comparison.alpha == pytest.approx(0.0, abs=1e-9)


def test_relative_drawdown_is_bounded_when_strategy_underperforms() -> None:
    # Strategy declines while the benchmark rises -> the relative-equity (ratio) drawdown is
    # in [-1, 0] and finite. The old return-difference compounding could fall below -1 here.
    index = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
    bench = pd.Series(0.001, index=index)
    strat = pd.Series(-0.002, index=index)
    comparison = BenchmarkComparator().compare(strat, bench)
    drawdown = comparison.benchmark_relative_drawdown
    assert np.isfinite(drawdown)
    assert -1.0 <= drawdown < 0.0


def test_relative_drawdown_includes_first_period_underperformance() -> None:
    index = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    comparison = BenchmarkComparator().compare(
        pd.Series([-0.10, 0.0], index=index), pd.Series([0.0, 0.0], index=index)
    )
    assert comparison.benchmark_relative_drawdown == pytest.approx(-0.10)


@pytest.mark.parametrize(
    ("strategy", "benchmark"),
    [([0.01], [0.0]), ([0.01, np.nan], [0.0, 0.0]), ([-1.0, 0.0], [0.0, 0.0])],
)
def test_comparison_rejects_insufficient_or_invalid_evidence(
    strategy: list[float], benchmark: list[float]
) -> None:
    with pytest.raises(ValueError, match="returns"):
        BenchmarkComparator().compare(pd.Series(strategy), pd.Series(benchmark))


def test_constant_benchmark_does_not_divide_by_zero() -> None:
    index = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    flat_bench = pd.Series(0.0, index=index)
    strat = pd.Series(0.001, index=index)
    comparison = BenchmarkComparator().compare(strat, flat_bench)
    assert comparison.beta == 0.0
    assert np.isfinite(comparison.alpha)


def test_default_benchmark_symbol_is_spy() -> None:
    assert BenchmarkComparator().benchmark_symbol == "SPY"


def test_relative_drawdown_survives_common_wealth_overflow() -> None:
    comparison = BenchmarkComparator().compare(
        pd.Series([0.5] * 2000 + [-0.2]), pd.Series([0.5] * 2000 + [0.2])
    )
    assert comparison.benchmark_relative_drawdown == pytest.approx(0.8 / 1.2 - 1)


@pytest.mark.parametrize("side", ["strategy", "benchmark", "both"])
@pytest.mark.parametrize("labels", [[0, 0, 1], [2, 1, 0], [0, 2, 1]])
def test_comparison_rejects_ambiguous_calendar_identity(side: str, labels: list[int]) -> None:
    ordered = pd.Series([0.01, 0.02, 0.03], index=[0, 1, 2])
    malformed = pd.Series([0.01, 0.02, 0.03], index=labels)
    strategy = malformed if side in {"strategy", "both"} else ordered
    benchmark = malformed if side in {"benchmark", "both"} else ordered
    with pytest.raises(ValueError, match=r"index.*unique.*ascending"):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("timezone", [None, "UTC"])
def test_comparison_preserves_valid_partial_date_overlap(timezone: str | None) -> None:
    index = pd.date_range("2026-01-01", periods=4, tz=timezone)
    strategy = pd.Series([0.1, -0.2, 0.25], index=index[:3])
    benchmark = pd.Series([0.0, 0.0, 0.0], index=index[1:])
    comparison = BenchmarkComparator().compare(strategy, benchmark)
    pd.testing.assert_series_equal(comparison.excess_returns, strategy.iloc[1:])
    assert comparison.benchmark_relative_drawdown == pytest.approx(-0.2)


def test_relative_drawdown_survives_common_wealth_underflow() -> None:
    comparison = BenchmarkComparator().compare(
        pd.Series([-0.5] * 2000 + [-0.2]), pd.Series([-0.5] * 2000 + [0.2])
    )
    assert comparison.benchmark_relative_drawdown == pytest.approx(0.8 / 1.2 - 1)


def test_relative_drawdown_survives_relative_wealth_overflow() -> None:
    comparison = BenchmarkComparator().compare(
        pd.Series([0.5] * 2000 + [-0.2]), pd.Series([0.0] * 2001)
    )
    assert comparison.benchmark_relative_drawdown == pytest.approx(-0.2)


def test_relative_drawdown_extreme_loss_remains_bounded() -> None:
    comparison = BenchmarkComparator().compare(pd.Series([-0.5] * 2000), pd.Series([0.0] * 2000))
    assert comparison.benchmark_relative_drawdown == -1.0


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=30,
    )
)
def test_relative_drawdown_matches_independent_product_ratio_oracle(
    pairs: list[tuple[float, float]],
) -> None:
    strategy = pd.Series([pair[0] for pair in pairs])
    benchmark = pd.Series([pair[1] for pair in pairs])
    wealth = np.concatenate(
        ([1.0], np.cumprod(1 + strategy.to_numpy()) / np.cumprod(1 + benchmark.to_numpy()))
    )
    expected = float((wealth / np.maximum.accumulate(wealth) - 1).min())
    comparator = BenchmarkComparator()
    actual = comparator.compare(strategy, benchmark).benchmark_relative_drawdown
    assert -1 <= actual <= 0
    assert actual == pytest.approx(expected, abs=1e-12)
    # Matched common growth contributes no relative movement, regardless of standalone scale.
    prefixed = comparator.compare(
        pd.Series([0.5] * 2000 + strategy.tolist()),
        pd.Series([0.5] * 2000 + benchmark.tolist()),
    ).benchmark_relative_drawdown
    assert prefixed == pytest.approx(actual, abs=1e-12)


@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize(
    "malformed",
    [
        pd.Series([0.01 + 2j, 0.02 + 3j, 0.03 + 4j]),
        pd.Series([True, False, True]),
        pd.Series([True, False, True], dtype="boolean"),
        pd.Series([0.01, 0.02, 0.03], dtype=object),
        pd.Series(["0.01", "0.02", "0.03"]),
    ],
)
def test_comparison_rejects_nonreal_return_dtypes(side: str, malformed: pd.Series) -> None:
    valid = pd.Series([0.01, 0.02, 0.03])
    strategy = malformed if side == "strategy" else valid
    benchmark = malformed if side == "benchmark" else valid
    with pytest.raises(ValueError, match=r"returns.*numeric"):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize("dtype", ["Float64", "Int64"])
def test_comparison_rejects_missing_aligned_nullable_returns(side: str, dtype: str) -> None:
    missing = pd.Series([0, pd.NA, 1], dtype=dtype)
    valid = pd.Series([0.01, 0.02, 0.03])
    strategy = missing if side == "strategy" else valid
    benchmark = missing if side == "benchmark" else valid
    with pytest.raises(ValueError, match=r"returns.*finite"):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("dtype", ["float64", "int64", "Float64", "Int64"])
def test_comparison_preserves_complete_numeric_return_dtypes(dtype: str) -> None:
    strategy = pd.Series([0, 1, 0], dtype=dtype)
    benchmark = pd.Series([1, 0, 0], dtype=dtype)
    actual = BenchmarkComparator().compare(strategy, benchmark)
    expected = BenchmarkComparator().compare(strategy.astype(float), benchmark.astype(float))
    np.testing.assert_array_equal(
        actual.excess_returns.to_numpy(dtype=float), expected.excess_returns
    )
    for field in (
        "alpha",
        "beta",
        "information_ratio",
        "tracking_error",
        "benchmark_relative_drawdown",
    ):
        assert getattr(actual, field) == pytest.approx(getattr(expected, field))


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_comparison_preserves_aligned_only_value_validation(dtype: str) -> None:
    strategy = pd.Series([np.nan, 0.01, 0.02], index=[0, 1, 2], dtype=dtype)
    benchmark = pd.Series([0.01, 0.02, -2], index=[1, 2, 3], dtype=dtype)
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(1)
    assert result.alpha == pytest.approx(0)
    assert result.tracking_error == pytest.approx(0)
    assert result.benchmark_relative_drawdown == pytest.approx(0)


@pytest.mark.parametrize("values", [[1e200, 2e200, 3e200], [1e308, 1e308, 1e308]])
@pytest.mark.parametrize("strict", [False, True])
def test_comparison_rejects_nonfinite_statistics(values: list[float], strict: bool) -> None:
    returns = pd.Series(values)
    with (
        np.errstate(all="raise" if strict else "ignore"),
        pytest.raises(ValueError, match=r"statistics.*finite"),
    ):
        BenchmarkComparator().compare(returns, returns)


def test_comparison_preserves_large_representable_constant_statistics() -> None:
    result = BenchmarkComparator().compare(pd.Series([1e100] * 3), pd.Series([1e100] * 3))
    assert result.beta == 0
    assert result.alpha == pytest.approx(252e100)
    assert result.information_ratio == 0
    assert result.tracking_error == 0
    assert result.benchmark_relative_drawdown == 0


@given(st.floats(min_value=1e160, max_value=1e250, allow_nan=False, allow_infinity=False))
def test_comparison_declines_overflowing_moments_without_publishing_nan(scale: float) -> None:
    returns = pd.Series([scale, 2 * scale, 3 * scale])
    with pytest.raises(ValueError, match=r"statistics.*finite"):
        BenchmarkComparator().compare(returns, returns)
