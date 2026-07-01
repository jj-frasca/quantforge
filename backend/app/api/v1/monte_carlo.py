from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.backtest import _MIN_BARS, _load_frame
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.research.backtesting.engine import BacktestEngine
from app.research.simulation.risk import analyze_strategy_risk
from app.research.strategies.builder import build_strategy
from app.research.strategies.configs import StrategyConfig

router = APIRouter(tags=["monte-carlo"])


class MonteCarloRequest(BaseModel):
    symbol: str
    strategy: StrategyConfig
    start_date: datetime
    end_date: datetime
    horizon_days: int = Field(default=252, ge=1)
    n_paths: int = Field(default=10_000, ge=1)
    loss_threshold: float = Field(default=0.2, gt=0, le=1)
    seed: int = 42
    initial_capital: float = Field(default=100_000.0, gt=0)
    cost_rate: float = Field(default=0.001, ge=0)


class MonteCarloResponse(BaseModel):
    symbol: str
    strategy_name: str
    parameters: dict[str, float | int]
    horizon_days: int
    n_paths: int
    loss_threshold: float
    # P(strategy ends the horizon down more than loss_threshold).
    prob_terminal_loss: float
    # P(worst intra-horizon drawdown breaches loss_threshold), always >= prob_terminal_loss.
    prob_max_drawdown_exceeds: float
    terminal_return_p5: float
    terminal_return_p50: float
    terminal_return_p95: float
    expected_terminal_return: float


# Sync handler (ADR-009): yfinance fetch + DB calls are blocking; FastAPI threadpools `def`.
@router.post("/monte-carlo", response_model=MonteCarloResponse)
def monte_carlo(
    request: MonteCarloRequest,
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
) -> MonteCarloResponse:
    frame = _load_frame(request.symbol, request.start_date, request.end_date, adapter, repository)
    if len(frame) < _MIN_BARS:
        raise HTTPException(
            status_code=422,
            detail=f"insufficient data: {len(frame)} bars (need >= {_MIN_BARS})",
        )
    strategy = build_strategy(request.strategy)
    engine = BacktestEngine(initial_capital=request.initial_capital, cost_rate=request.cost_rate)
    result = engine.run_strategy(frame, strategy)
    risk = analyze_strategy_risk(
        result.returns,
        horizon_days=request.horizon_days,
        n_paths=request.n_paths,
        loss_threshold=request.loss_threshold,
        seed=request.seed,
    )
    return MonteCarloResponse(
        symbol=request.symbol,
        strategy_name=strategy.name,
        parameters={k: v for k, v in strategy.parameters.items() if isinstance(v, int | float)},
        horizon_days=risk.horizon_days,
        n_paths=risk.n_paths,
        loss_threshold=risk.loss_threshold,
        prob_terminal_loss=risk.prob_terminal_loss,
        prob_max_drawdown_exceeds=risk.prob_max_drawdown_exceeds,
        terminal_return_p5=risk.terminal_return_p5,
        terminal_return_p50=risk.terminal_return_p50,
        terminal_return_p95=risk.terminal_return_p95,
        expected_terminal_return=risk.expected_terminal_return,
    )
