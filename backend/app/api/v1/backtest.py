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
from app.research.strategies.builder import build_strategy
from app.research.strategies.configs import StrategyConfig

router = APIRouter(tags=["backtest"])

_MIN_BARS = 30
_ROLLING_SHARPE_WINDOW = 60
_TRADING_DAYS = 252
_RETURN_HIST_BINS = 30


class BacktestRequest(BaseModel):
    symbol: str
    strategy: StrategyConfig
    start_date: datetime
    end_date: datetime
    # Engine knobs the API caller can override. Both default to the BacktestEngine's
    # constructor defaults (100_000 starting capital, 10 bps cost per unit turnover).
    # Exposed via the form so the user can sanity-check what costs do to the equity
    # curve — the most under-appreciated variable in retail backtests.
    initial_capital: float = Field(default=100_000.0, gt=0)
    cost_rate: float = Field(default=0.001, ge=0)


class EquityPoint(BaseModel):
    timestamp_utc: datetime
    equity: float


class BacktestMetricsView(BaseModel):
    sharpe: float
    max_drawdown: float
    total_return: float
    annualized_return: float
    annualized_vol: float


class DrawdownPoint(BaseModel):
    timestamp_utc: datetime
    drawdown: float  # in [-1, 0]; 0 == at peak


class RollingSharpePoint(BaseModel):
    timestamp_utc: datetime
    sharpe: float


class TradeMarker(BaseModel):
    """A single position-direction change.

    Notes:
        `direction` is "buy" when the new position is greater than the prior one
        (entering long OR covering short OR flipping short -> long), "sell" when
        the new position is less than the prior one. `equity` is the strategy's
        equity at the bar where the signal flipped — used as the y-coordinate
        when the marker is overlaid on the equity-curve chart.
    """

    timestamp_utc: datetime
    direction: Literal["buy", "sell"]
    equity: float


class ReturnBin(BaseModel):
    bin_center: float
    frequency: int


class ReturnDistribution(BaseModel):
    bins: list[ReturnBin]
    skewness: float
    kurtosis: float  # excess kurtosis (Gaussian == 0)


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
    # Drawdown series (equity / cummax - 1) for the underwater plot. Same time index.
    drawdown_curve: list[DrawdownPoint]
    # Rolling Sharpe (annualized, window = ROLLING_SHARPE_WINDOW bars). Before the window
    # fills, sharpe is 0.0. Shows whether the strategy's edge is stable or concentrated.
    rolling_sharpe_curve: list[RollingSharpePoint]
    rolling_sharpe_window: int
    # Distribution of daily returns (histogram bins + skew + excess kurtosis). Fat tails
    # are the bug, not the feature — a sharp left tail is the most honest risk warning.
    return_distribution: ReturnDistribution
    # Discrete position-flip events for the equity-curve overlay. Bars where the signal
    # changed direction; empty if the strategy never moved (a stuck-flat regime).
    trade_markers: list[TradeMarker]


def _series_to_curve(series: "pd.Series") -> list[EquityPoint]:
    return [EquityPoint(timestamp_utc=ts, equity=float(value)) for ts, value in series.items()]


def _equity_to_drawdown(equity: "pd.Series") -> list[DrawdownPoint]:
    dd = equity / equity.cummax() - 1.0
    return [DrawdownPoint(timestamp_utc=ts, drawdown=float(value)) for ts, value in dd.items()]


def _trade_markers(position: "pd.Series", equity: "pd.Series") -> list[TradeMarker]:
    """Position-direction changes as discrete trade events for the equity-curve overlay.

    Notes:
        We mark the bar where the SIGNAL changes (position.diff != 0), which is the bar
        the user sees on the chart. The engine actually trades on the NEXT bar
        (`position.shift(1)`), but the SIGNAL is what drives a trader's mental model.
        First bar uses `position.diff().fillna(0)` so a strategy that starts long
        doesn't appear to "buy from nothing" on bar 0 — that's the engine's responsibility,
        not a trade event we want to surface.
    """
    # Iterate positionally (index, diff, equity all aligned) rather than looking up
    # equity.loc[ts]: real data can carry a duplicated bar timestamp, and a label lookup
    # on a non-unique index returns a Series — float() then raises and the route 500s.
    diff = position.diff().fillna(0.0)
    markers: list[TradeMarker] = []
    for ts, change, eq in zip(diff.index, diff.to_numpy(), equity.to_numpy(), strict=True):
        if change == 0.0:
            continue
        direction: Literal["buy", "sell"] = "buy" if change > 0 else "sell"
        markers.append(TradeMarker(timestamp_utc=ts, direction=direction, equity=float(eq)))
    return markers


def _return_distribution(returns: "pd.Series", bins: int) -> ReturnDistribution:
    """Histogram + higher moments of the daily return series.

    Notes:
        Excess kurtosis (Fisher convention) — a Gaussian is 0. Positive means fatter
        tails than normal; negative means thinner. Skewness < 0 (left-skew) is the most
        dangerous shape: small wins, occasional large losses.
    """
    import numpy as np

    values = returns.to_numpy()
    if values.size == 0:
        return ReturnDistribution(bins=[], skewness=0.0, kurtosis=0.0)
    counts, edges = np.histogram(values, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    bin_list = [
        ReturnBin(bin_center=float(c), frequency=int(n))
        for c, n in zip(centers, counts, strict=True)
    ]

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
    if std == 0.0 or not np.isfinite(std):
        return ReturnDistribution(bins=bin_list, skewness=0.0, kurtosis=0.0)
    centered = values - mean
    skew = float(np.mean(centered**3) / std**3)
    kurt = float(np.mean(centered**4) / std**4 - 3.0)  # Fisher / excess
    return ReturnDistribution(bins=bin_list, skewness=skew, kurtosis=kurt)


def _rolling_sharpe(returns: "pd.Series", window: int) -> list[RollingSharpePoint]:
    """Annualized rolling Sharpe with a fixed window.

    Notes:
        Before the window fills, sharpe is 0.0 (not NaN — keeps the wire JSON-clean).
        std==0 is also 0.0 (a degenerate window).
    """
    import math

    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    sqrt_t = math.sqrt(_TRADING_DAYS)
    sharpe = sqrt_t * (mean / std.where(std > 0))
    sharpe = sharpe.fillna(0.0)
    return [RollingSharpePoint(timestamp_utc=ts, sharpe=float(v)) for ts, v in sharpe.items()]


def _to_response(
    symbol: str,
    strategy: BaseStrategy,
    result: BacktestResult,
    prices: "pd.Series",
    initial_capital: float,
    strategy_returns: "pd.Series",
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
        drawdown_curve=_equity_to_drawdown(result.equity_curve),
        rolling_sharpe_curve=_rolling_sharpe(strategy_returns, _ROLLING_SHARPE_WINDOW),
        rolling_sharpe_window=_ROLLING_SHARPE_WINDOW,
        return_distribution=_return_distribution(strategy_returns, _RETURN_HIST_BINS),
        trade_markers=_trade_markers(result.position, result.equity_curve),
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
    strategy = build_strategy(request.strategy)
    engine = BacktestEngine(
        initial_capital=request.initial_capital,
        cost_rate=request.cost_rate,
    )
    result = engine.run_strategy(frame, strategy)
    return _to_response(
        request.symbol,
        strategy,
        result,
        frame["close"],
        engine.initial_capital,
        result.returns,
    )
