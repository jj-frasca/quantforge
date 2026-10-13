from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from app.research.backtesting.metrics import TRADING_DAYS

_MASKED_NUMERIC_DTYPES = (
    pd.Float32Dtype,
    pd.Float64Dtype,
    pd.Int8Dtype,
    pd.Int16Dtype,
    pd.Int32Dtype,
    pd.Int64Dtype,
    pd.UInt8Dtype,
    pd.UInt16Dtype,
    pd.UInt32Dtype,
    pd.UInt64Dtype,
)
_MASKED_UNSIGNED_DTYPES = (pd.UInt8Dtype, pd.UInt16Dtype, pd.UInt32Dtype, pd.UInt64Dtype)
_MASKED_INTEGER_DTYPES = (
    pd.Int8Dtype,
    pd.Int16Dtype,
    pd.Int32Dtype,
    pd.Int64Dtype,
    *_MASKED_UNSIGNED_DTYPES,
)


@dataclass(frozen=True)
class BenchmarkComparison:
    excess_returns: pd.Series
    information_ratio: float
    alpha: float
    beta: float
    tracking_error: float
    benchmark_relative_drawdown: float


def _anchored_native_wide_beta(strategy: pd.Series, benchmark: pd.Series) -> float:
    """Match wider centered sums without narrowing or unused variance (ADR-270)."""
    try:
        with np.errstate(under="raise"):
            strategy_values = strategy.to_numpy(dtype=np.longdouble)
            benchmark_values = benchmark.to_numpy(dtype=np.longdouble)
            strategy_delta = strategy_values - strategy_values[0]
            benchmark_delta = benchmark_values - benchmark_values[0]
            strategy_dev = strategy_delta - strategy_delta.mean()
            benchmark_dev = benchmark_delta - benchmark_delta.mean()
            denominator = np.longdouble(np.sum(benchmark_dev * benchmark_dev))
            if not np.isfinite(denominator) or denominator <= 0:
                raise ValueError("native-wide beta denominator must be positive and finite")
            numerator = np.longdouble(np.sum(strategy_dev * benchmark_dev))
            return float(numerator / denominator)
    except FloatingPointError as exc:
        raise ValueError("native-wide beta moments must be measurable") from exc


def _exact_unsigned_excess(strategy: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Certify integer differences for pairs containing unsigned returns (ADR-273/274)."""
    differences = [int(a) - int(b) for a, b in zip(strategy, benchmark, strict=True)]
    values = np.asarray(differences, dtype=np.longdouble)
    if any(
        value.as_integer_ratio() != (difference, 1)
        for value, difference in zip(values, differences, strict=True)
    ):
        raise ValueError("unsigned excess differences must be exactly representable")
    name = (
        pd.Series(dtype=float, name=strategy.name) - pd.Series(dtype=float, name=benchmark.name)
    ).name
    return pd.Series(values, index=strategy.index, name=name)


def _anchored_native_wide_excess_std(excess: pd.Series) -> np.longdouble:
    """Retain wider sample dispersion through final statistics (ADR-272)."""
    try:
        with np.errstate(under="raise"):
            values = excess.to_numpy(dtype=np.longdouble)
            delta = values - values[0]
            deviations = delta - delta.mean()
            variance = np.longdouble(np.sum(deviations * deviations) / (len(values) - 1))
            if not np.isfinite(variance) or variance <= 0:
                raise ValueError("native-wide excess dispersion must be measurable")
            return np.longdouble(np.sqrt(variance))
    except FloatingPointError as exc:
        raise ValueError("native-wide excess dispersion must be measurable") from exc


class BenchmarkComparator:
    """Compares a strategy's returns to a benchmark (default SPY), backtesting-spec.md §5.

    Notes:
        Absolute Sharpe is never the whole story — every BacktestResult is reported against a
        benchmark. SPY-vs-SPY is the oracle: excess≈0, IR≈0, alpha≈0, beta≈1.
    """

    def __init__(self, benchmark_symbol: str = "SPY") -> None:
        self.benchmark_symbol = benchmark_symbol

    def compare(
        self, strategy_returns: pd.Series, benchmark_returns: pd.Series
    ) -> BenchmarkComparison:
        for returns in (strategy_returns, benchmark_returns):
            if not returns.index.is_unique or not returns.index.is_monotonic_increasing:
                raise ValueError("returns index must be unique and ascending")
            if (
                not is_numeric_dtype(returns.dtype)
                or is_bool_dtype(returns.dtype)
                or is_complex_dtype(returns.dtype)
            ):
                raise ValueError("returns must be real nonboolean numeric observations")
        strat, bench = strategy_returns.align(benchmark_returns, join="inner")
        if len(strat) < 2:
            raise ValueError("returns must have at least two aligned observations")
        strat_values = strat.to_numpy(dtype=np.float64, na_value=np.nan)
        bench_values = bench.to_numpy(dtype=np.float64, na_value=np.nan)
        if not np.isfinite(strat_values).all() or not np.isfinite(bench_values).all():
            raise ValueError("returns must be finite")
        if np.any(strat_values <= -1.0) or np.any(bench_values <= -1.0):
            raise ValueError("returns must preserve positive wealth")
        wide_source = any(
            isinstance(returns.dtype, np.dtype)
            and returns.dtype.kind == "f"
            and returns.dtype.itemsize > np.dtype(float).itemsize
            for returns in (strat, bench)
        )
        unsigned_sources = all(
            (isinstance(returns.dtype, np.dtype) and returns.dtype.kind == "u")
            or isinstance(returns.dtype, _MASKED_UNSIGNED_DTYPES)
            for returns in (strat, bench)
        )
        mixed_integer_sources = {strat.dtype.kind, bench.dtype.kind} == {"i", "u"} and all(
            isinstance(returns.dtype, (np.dtype, *_MASKED_INTEGER_DTYPES))
            for returns in (strat, bench)
        )
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            if unsigned_sources or mixed_integer_sources:
                excess = _exact_unsigned_excess(strat, bench)
            elif wide_source and any(
                isinstance(returns.dtype, _MASKED_NUMERIC_DTYPES) for returns in (strat, bench)
            ):
                # Pandas has no wider masked dtype. Preserve original values in a plain Series.
                # Empty ordinary operands retain pandas name consensus, including NaN/NA.
                excess_name = (
                    pd.Series(dtype=float, name=strat.name)
                    - pd.Series(dtype=float, name=bench.name)
                ).name
                excess = pd.Series(
                    strat.to_numpy(dtype=np.longdouble) - bench.to_numpy(dtype=np.longdouble),
                    index=strat.index,
                    name=excess_name,
                )
            else:
                excess = strat - bench

            # Exact native constants have zero covariance before rounded centering (ADR-269).
            constant_source = bool(strat.eq(strat.iloc[0]).all() or bench.eq(bench.iloc[0]).all())
            needs_scaled = False
            try:
                with np.errstate(under="raise"):
                    if wide_source and not constant_source:
                        native_beta = _anchored_native_wide_beta(strat, bench)
                    else:
                        bench_var = 0.0 if constant_source else float(bench.var())
                        needs_scaled = bench_var == 0.0
                        native_beta = float(strat.cov(bench) / bench_var) if bench_var > 0 else 0.0
            except FloatingPointError:
                # Positive variance/covariance can also lose evidence to underflow (ADR-268).
                # Reuse scaled recovery without changing the native path otherwise.
                needs_scaled, native_beta = True, 0.0
            if not constant_source and needs_scaled and np.any(bench_values != bench_values[0]):
                # A nonconstant benchmark is not the constant-series convention: sample
                # squares can underflow. Scale the same covariance ratio (ADR-181).
                bench_scale = float(np.abs(bench_values).max())
                strat_scale = float(np.abs(strat_values).max())
                if strat_scale == 0.0:
                    beta = 0.0
                else:
                    scaled_bench = bench / bench_scale
                    scaled_strat = strat / strat_scale
                    scaled_var = float(scaled_bench.var())
                    if not np.isfinite(scaled_var) or scaled_var <= 0.0:
                        raise ValueError(
                            "normalized benchmark variance must be positive and finite"
                        )
                    scaled_beta = float(scaled_strat.cov(scaled_bench) / scaled_var)
                    beta = scaled_beta * (strat_scale / bench_scale) if scaled_beta != 0.0 else 0.0
            else:
                beta = native_beta
            alpha = float((strat.mean() - beta * bench.mean()) * TRADING_DAYS)

            if excess.eq(excess.iloc[0]).all():
                excess_std: float | np.longdouble = 0.0
            elif (
                isinstance(excess.dtype, np.dtype)
                and excess.dtype.kind == "f"
                and excess.dtype.itemsize > np.dtype(float).itemsize
            ):
                excess_std = _anchored_native_wide_excess_std(excess)
            else:
                excess_std = float(excess.std())
            sqrt_t = np.sqrt(TRADING_DAYS)
            information_ratio = (
                float(sqrt_t * excess.mean() / excess_std) if excess_std > 0 else 0.0
            )
            tracking_error = float(sqrt_t * excess_std)
            # Relative drawdown = drawdown of the strategy's equity RELATIVE to the benchmark's
            # (a ratio of compounded curves, always positive). Compounding the return *difference*
            # (strat - bench) is invalid — it can fall to <= -1 and yield a meaningless curve.
            # Shared growth must cancel before compounding: standalone wealth can overflow or
            # underflow even when its ratio is representable. Running log peaks avoid materializing
            # large relative wealth too (ADR-171); zero is the pre-return unit-wealth baseline.
            relative_log_wealth = np.concatenate(
                ([0.0], np.cumsum(np.log1p(strat_values) - np.log1p(bench_values)))
            )
            log_drawdown = relative_log_wealth - np.maximum.accumulate(relative_log_wealth)

            comparison = BenchmarkComparison(
                excess_returns=excess,
                information_ratio=information_ratio,
                alpha=alpha,
                beta=beta,
                tracking_error=tracking_error,
                benchmark_relative_drawdown=float(np.expm1(log_drawdown.min())),
            )
        statistics = (
            comparison.alpha,
            comparison.beta,
            comparison.information_ratio,
            comparison.tracking_error,
            comparison.benchmark_relative_drawdown,
        )
        if not np.isfinite(statistics).all():
            raise ValueError("benchmark statistics must be finite")
        return comparison
