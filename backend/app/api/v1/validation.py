from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.data.pipelines.ingestion import DataIngestionPipeline
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.research.frames import bars_to_frame
from app.research.strategies.base import BaseStrategy
from app.research.strategies.mean_reversion import MeanReversionStrategy
from app.research.strategies.momentum import MomentumStrategy
from app.research.strategies.sma import SMAStrategy
from app.validation.engine import ValidationEngine
from app.validation.report import ValidationReport

router = APIRouter(tags=["validation"])

StrategyName = Literal["sma", "momentum", "mean_reversion"]
_MIN_BARS = 30


class ValidateRequest(BaseModel):
    symbol: str
    strategy: StrategyName
    start_date: datetime
    end_date: datetime


def _config_grid(strategy: StrategyName) -> list[BaseStrategy]:
    if strategy == "sma":
        return [
            SMAStrategy(fast=f, slow=s)
            for f, s in [(5, 20), (10, 30), (15, 40), (20, 50), (5, 30), (10, 40)]
        ]
    if strategy == "momentum":
        return [
            MomentumStrategy(lookback=lb, skip=sk)
            for lb, sk in [(20, 2), (40, 5), (60, 5), (30, 2)]
        ]
    return [
        MeanReversionStrategy(window=w, k=k)
        for w, k in [(10, 2.0), (20, 2.0), (20, 1.5), (30, 2.5)]
    ]


# Sync endpoint on purpose: FastAPI runs `def` handlers in a threadpool, so the blocking
# yfinance fetch and DB calls don't stall the event loop (ADR-009 sync stack).
@router.post("/validate", response_model=ValidationReport)
def validate(
    request: ValidateRequest,
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
) -> ValidationReport:
    bars = repository.get_bars(request.symbol, request.start_date, request.end_date)
    if len(bars) < _MIN_BARS:
        # Cache miss: run the ingestion pipeline (quality gate persists either way; bars
        # are stored only if the gate passes), then re-read from the repo.
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
    return ValidationEngine().validate(request.strategy, _config_grid(request.strategy), frame)
