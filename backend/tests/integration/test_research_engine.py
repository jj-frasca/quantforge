import pytest
from tests.fixtures.synthetic import builders

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.manifest import ExperimentManifest, compute_parameter_hash
from app.research.benchmarks.comparator import BenchmarkComparator
from app.research.frames import bars_to_frame
from app.research.strategies.base import BaseStrategy
from app.research.strategies.mean_reversion import MeanReversionStrategy
from app.research.strategies.momentum import MomentumStrategy
from app.research.strategies.sma import SMAStrategy

_STRATEGIES: list[BaseStrategy] = [
    SMAStrategy(fast=5, slow=10),
    MomentumStrategy(lookback=20, skip=2),
    MeanReversionStrategy(window=10, k=2.0),
]


@pytest.mark.parametrize("strategy", _STRATEGIES, ids=lambda s: s.name)
def test_strategy_runs_end_to_end_with_benchmark_and_manifest(strategy: BaseStrategy) -> None:
    frame = bars_to_frame(builders.clean_series(n=120))

    # 1. backtest through the engine with transaction costs
    result = BacktestEngine(initial_capital=100_000.0, cost_rate=0.001).run_strategy(
        frame, strategy
    )
    assert len(result.equity_curve) == 120
    assert result.cost_rate == 0.001
    assert -1.0 <= result.metrics.max_drawdown <= 0.0

    # 2. benchmark comparison (buy-and-hold proxy) is computed for every result
    benchmark_returns = frame["close"].pct_change().fillna(0.0)
    comparison = BenchmarkComparator().compare(result.returns, benchmark_returns)
    assert len(comparison.excess_returns) == 120

    # 3. a reproducible ExperimentManifest is produced
    manifest = ExperimentManifest(
        git_commit_hash="test-commit",
        strategy_name=strategy.name,
        parameter_hash=compute_parameter_hash(strategy.parameters),
        data_source="synthetic",
        symbol="AAPL",
        start_date=frame.index[0].date(),
        end_date=frame.index[-1].date(),
        adapter_version="synthetic-1",
    )
    assert manifest.strategy_name == strategy.name
    assert ExperimentManifest.model_validate_json(manifest.model_dump_json()) == manifest
