from datetime import datetime
from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.data.pipelines.ingestion import DataIngestionPipeline
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.research.backtesting.engine import BacktestEngine, BacktestResult
from app.research.frames import bars_to_frame
from app.research.strategies.base import BaseStrategy
from app.research.strategies.mean_reversion import MeanReversionStrategy
from app.research.strategies.momentum import MomentumStrategy
from app.research.strategies.sma import SMAStrategy

router = APIRouter(tags=["backtest"])

_MIN_BARS = 30


class SMAConfig(BaseModel):
    name: Literal["sma"] = "sma"
    fast: int = Field(default=20, ge=1)
    slow: int = Field(default=50, ge=2)


class MomentumConfig(BaseModel):
    name: Literal["momentum"] = "momentum"
    lookback: int = Field(default=60, ge=1)
    skip: int = Field(default=5, ge=0)


class MeanReversionConfig(BaseModel):
    name: Literal["mean_reversion"] = "mean_reversion"
    window: int = Field(default=20, ge=2)
    k: float = Field(default=2.0, gt=0)


StrategyConfig = Annotated[
    SMAConfig | MomentumConfig | MeanReversionConfig,
    Field(discriminator="name"),
]


class BacktestRequest(BaseModel):
    symbol: str
    strategy: StrategyConfig
    start_date: datetime
    end_date: datetime


class EquityPoint(BaseModel):
    timestamp_utc: datetime
    equity: float


class BacktestMetricsView(BaseModel):
    sharpe: float
    max_drawdown: float
    total_return: float
    annualized_return: float
    annualized_vol: float


class BacktestResponse(BaseModel):
    symbol: str
    strategy_name: str
    parameters: dict[str, float | int]
    n_trades: int
    cost_rate: float
    metrics: BacktestMetricsView
    equity_curve: list[EquityPoint]
    # Buy-and-hold of the SAME symbol: the canonical "is the strategy doing anything?"
    # check. Same time index as `equity_curve`; same `initial_capital` starting point.
    buy_and_hold_curve: list[EquityPoint]
    buy_and_hold_total_return: float


def _build_strategy(config: StrategyConfig) -> BaseStrategy:
    if isinstance(config, SMAConfig):
        return SMAStrategy(fast=config.fast, slow=config.slow)
    if isinstance(config, MomentumConfig):
        return MomentumStrategy(lookback=config.lookback, skip=config.skip)
    return MeanReversionStrategy(window=config.window, k=config.k)


def _series_to_curve(series: "pd.Series") -> list[EquityPoint]:
    return [EquityPoint(timestamp_utc=ts, equity=float(value)) for ts, value in series.items()]


def _to_response(
    symbol: str,
    strategy: BaseStrategy,
    result: BacktestResult,
    prices: "pd.Series",
    initial_capital: float,
) -> BacktestResponse:
    # Buy-and-hold equity: a 100% long position from t=0, same starting capital, no costs.
    bh_returns = prices.pct_change().fillna(0.0)
    bh_equity = (1.0 + bh_returns).cumprod() * initial_capital
    bh_total_return = float(bh_equity.iloc[-1] / bh_equity.iloc[0] - 1.0)
    return BacktestResponse(
        symbol=symbol,
        strategy_name=strategy.name,
        parameters={k: v for k, v in strategy.parameters.items() if isinstance(v, int | float)},
        n_trades=result.n_trades,
        cost_rate=result.cost_rate,
        metrics=BacktestMetricsView(
            sharpe=result.metrics.sharpe,
            max_drawdown=result.metrics.max_drawdown,
            total_return=result.metrics.total_return,
            annualized_return=result.metrics.annualized_return,
            annualized_vol=result.metrics.annualized_vol,
        ),
        equity_curve=_series_to_curve(result.equity_curve),
        buy_and_hold_curve=_series_to_curve(bh_equity),
        buy_and_hold_total_return=bh_total_return,
    )


# Sync handler (ADR-009): yfinance fetch + DB calls are blocking; FastAPI threadpools `def`.
@router.post("/backtest", response_model=BacktestResponse)
def backtest(
    request: BacktestRequest,
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
) -> BacktestResponse:
    # Cache-aside, same as /validate (data is the same shape).
    bars = repository.get_bars(request.symbol, request.start_date, request.end_date)
    if len(bars) < _MIN_BARS:
        DataIngestionPipeline(adapter, repository).ingest(
            request.symbol, request.start_date, request.end_date
        )
        bars = repository.get_bars(request.symbol, request.start_date, request.end_date)
    frame = bars_to_frame(bars)
    if len(frame) < _MIN_BARS:
        raise HTTPException(
            status_code=422,
            detail=f"insufficient data: {len(frame)} bars (need >= {_MIN_BARS})",
        )
    strategy = _build_strategy(request.strategy)
    engine = BacktestEngine()
    result = engine.run_strategy(frame, strategy)
    return _to_response(request.symbol, strategy, result, frame["close"], engine.initial_capital)
