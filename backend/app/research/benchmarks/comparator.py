from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from app.research.backtesting.metrics import TRADING_DAYS


@dataclass(frozen=True)
class BenchmarkComparison:
    excess_returns: pd.Series
    information_ratio: float
    alpha: float
    beta: float
    tracking_error: float
    benchmark_relative_drawdown: float


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
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            excess = strat - bench

            with np.errstate(under="ignore"):
                bench_var = float(bench.var())
            if bench_var == 0.0 and np.any(bench_values != bench_values[0]):
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
                beta = float(strat.cov(bench) / bench_var) if bench_var > 0 else 0.0
            alpha = float((strat.mean() - beta * bench.mean()) * TRADING_DAYS)

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
