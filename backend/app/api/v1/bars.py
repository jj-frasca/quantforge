from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.data.models import PriceBar
from app.data.pipelines.ingestion import validate_request_range
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository

router = APIRouter(tags=["bars"])


class ChartBar(BaseModel):
    """Slim chart-shaped projection of a PriceBar.

    Notes:
        Decimal -> float at the API boundary: charts work in floats and lose nothing
        meaningful at chart resolution. The canonical decimal-precision PriceBar stays
        the in-process truth (storage, backtesting, validation all use it).
    """

    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class BarsResponse(BaseModel):
    symbol: str
    n_bars: int
    bars: list[ChartBar]


def _to_chart(bar: PriceBar) -> ChartBar:
    return ChartBar(
        timestamp_utc=bar.timestamp_utc,
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=bar.volume,
    )


# Sync handler (ADR-009): blocking DB calls go through FastAPI's threadpool.
@router.get("/bars", response_model=BarsResponse)
def bars(
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    symbol: Annotated[str, Query(min_length=1)],
    start_date: Annotated[datetime, Query()],
    end_date: Annotated[datetime, Query()],
) -> BarsResponse:
    try:
        validate_request_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    cached = repository.get_bars(symbol, start_date, end_date, source=adapter.source)
    return BarsResponse(
        symbol=symbol.strip().upper(),
        n_bars=len(cached),
        bars=[_to_chart(b) for b in cached],
    )
