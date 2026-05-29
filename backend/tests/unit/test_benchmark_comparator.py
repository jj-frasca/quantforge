"""BenchmarkComparator: SPY-vs-SPY is neutral (excess≈0, IR≈0, alpha≈0, beta≈1), excess captures constant outperformance, 2x leverage → beta 2 / alpha 0, constant benchmark is division-safe."""

import numpy as np
import pandas as pd
import pytest

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


def test_constant_benchmark_does_not_divide_by_zero() -> None:
    index = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    flat_bench = pd.Series(0.0, index=index)
    strat = pd.Series(0.001, index=index)
    comparison = BenchmarkComparator().compare(strat, flat_bench)
    assert comparison.beta == 0.0
    assert np.isfinite(comparison.alpha)


def test_default_benchmark_symbol_is_spy() -> None:
    assert BenchmarkComparator().benchmark_symbol == "SPY"
