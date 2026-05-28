from dataclasses import dataclass

import pandas as pd

from app.research.backtesting.metrics import BacktestMetrics
from app.research.strategies.base import BaseStrategy


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    metrics: BacktestMetrics
    n_trades: int
    cost_rate: float


class BacktestEngine:
    """Vectorized pandas/numpy backtester (ADR-007, backtesting-spec.md §3).

    Notes:
        No look-ahead: yesterday's position earns today's return (``position.shift(1)``).
        Transaction costs are charged on turnover (|Δposition|). Long/short are symmetric.
    """

    def __init__(self, initial_capital: float = 100_000.0, cost_rate: float = 0.001) -> None:
        if initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")
        if cost_rate < 0:
            raise ValueError("cost_rate must be >= 0")
        self.initial_capital = initial_capital
        self.cost_rate = cost_rate

    def run(self, prices: pd.Series, signals: pd.Series) -> BacktestResult:
        returns = prices.pct_change().fillna(0.0)
        position = signals.reindex(prices.index).clip(-1.0, 1.0).fillna(0.0)

        gross = position.shift(1).fillna(0.0) * returns
        turnover = position.diff().abs().fillna(position.abs())
        net = gross - turnover * self.cost_rate

        equity_curve = (1.0 + net).cumprod() * self.initial_capital
        n_trades = int((turnover > 0).sum())

        return BacktestResult(
            equity_curve=equity_curve,
            returns=net,
            metrics=BacktestMetrics.from_series(net, equity_curve),
            n_trades=n_trades,
            cost_rate=self.cost_rate,
        )

    def run_strategy(self, data: pd.DataFrame, strategy: BaseStrategy) -> BacktestResult:
        """Convenience: generate signals from a strategy and backtest on the frame's close."""
        return self.run(data["close"], strategy.generate_signals(data))
