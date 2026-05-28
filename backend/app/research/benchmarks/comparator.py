from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.research.backtesting.metrics import TRADING_DAYS, max_drawdown


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
        strat, bench = strategy_returns.align(benchmark_returns, join="inner")
        excess = strat - bench

        bench_var = float(bench.var())
        beta = float(strat.cov(bench) / bench_var) if bench_var > 0 else 0.0
        alpha = float((strat.mean() - beta * bench.mean()) * TRADING_DAYS)

        excess_std = float(excess.std())
        sqrt_t = np.sqrt(TRADING_DAYS)
        information_ratio = float(sqrt_t * excess.mean() / excess_std) if excess_std > 0 else 0.0
        tracking_error = float(sqrt_t * excess_std)
        excess_equity = (1.0 + excess).cumprod()

        return BenchmarkComparison(
            excess_returns=excess,
            information_ratio=information_ratio,
            alpha=alpha,
            beta=beta,
            tracking_error=tracking_error,
            benchmark_relative_drawdown=max_drawdown(excess_equity),
        )
