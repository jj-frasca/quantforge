"""Exact constant sources have zero beta before rounded moment centering."""

from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator


@pytest.mark.parametrize("side", ["strategy", "benchmark", "both"])
@pytest.mark.parametrize("dtype", ["float64", "Float64", "float32", "Float32", np.longdouble])
def test_beta_exact_original_constant_sources_are_zero(side: str, dtype: object) -> None:
    constant = pd.Series([0.1] * 3, dtype=dtype)
    changing = pd.Series([0.01, 0.02, 0.03], dtype=dtype)
    strategy = constant if side in {"strategy", "both"} else changing
    benchmark = constant if side in {"benchmark", "both"} else changing
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
    if dtype in {"float32", "Float32"}:
        # ADR-280 retains beta zero while measuring the original strategy mean exactly.
        expected_alpha = float(
            252 * sum(Fraction(*value.as_integer_ratio()) for value in strategy) / len(strategy)
        )
    else:
        expected_alpha = float(strategy.mean() * 252)
    assert result.alpha == expected_alpha
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)
    pd.testing.assert_series_equal(result.excess_returns, strategy - benchmark)


@pytest.mark.parametrize("side", ["strategy", "benchmark", "both"])
def test_beta_constants_bypass_native_variance_and_covariance(
    side: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    constant = pd.Series([0.1] * 3)
    changing = pd.Series([0.01, 0.02, 0.03])
    strategy = constant if side in {"strategy", "both"} else changing
    benchmark = constant if side in {"benchmark", "both"} else changing

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("constant beta must not depend on rounded moments")

    monkeypatch.setattr(pd.Series, "var", forbidden)
    monkeypatch.setattr(pd.Series, "cov", forbidden)
    assert BenchmarkComparator().compare(strategy, benchmark).beta == 0


def test_beta_constant_check_uses_only_aligned_source_observations() -> None:
    strategy = pd.Series([999.0, 0.1, 0.1, 0.1], index=[0, 1, 2, 3])
    benchmark = pd.Series([0.01, 0.02, 0.03, 888.0], index=[1, 2, 3, 4])
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
    assert result.alpha == float(strategy.iloc[1:].mean() * 252)
    pd.testing.assert_series_equal(result.excess_returns, strategy.iloc[1:] - benchmark.iloc[:3])


def test_beta_native_wide_distinctions_are_not_float64_constants() -> None:
    base = np.longdouble("0.1")
    second = np.nextafter(base, np.longdouble(np.inf))
    third = np.nextafter(second, np.longdouble(np.inf))
    returns = pd.Series([base, second, third], dtype=np.longdouble)
    assert not returns.eq(returns.iloc[0]).all()
    if np.finfo(np.longdouble).nmant > np.finfo(float).nmant:
        assert np.all(returns.to_numpy(dtype=float) == float(base))
    # ADR-270 corrects the separately documented wider moment loss: same-series beta is one.
    result = BenchmarkComparator().compare(returns, returns)
    assert result.beta == 1
    assert result.beta != 0


@settings(max_examples=70, deadline=None)
@given(
    value=st.sampled_from([0.1, 0.2, 0.3, -0.1, 1e-162, 1e-200, 1e100]),
    n=st.integers(min_value=3, max_value=30),
    side=st.sampled_from(["strategy", "benchmark", "both"]),
)
def test_beta_repeated_represented_sources_have_exact_zero_covariance(
    value: float, n: int, side: str
) -> None:
    constant = pd.Series([value] * n)
    changing = pd.Series([0.01 * (i + 1) for i in range(n)])
    strategy = constant if side in {"strategy", "both"} else changing
    benchmark = constant if side in {"benchmark", "both"} else changing
    # Exact repeated source values have zero centered residuals and therefore zero covariance.
    assert constant.eq(constant.iloc[0]).all()
    state = np.geterr()
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert np.geterr() == state
    assert result.beta == 0
    assert result.alpha == float(strategy.mean() * 252)
