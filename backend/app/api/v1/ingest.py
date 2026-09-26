from datetime import datetime
from typing import Annotated, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, model_validator

from app.data.models import DataQualityReport
from app.data.pipelines.ingestion import DataIngestionPipeline, validate_request_range
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository

router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    symbol: str
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        validate_request_range(self.start_date, self.end_date)
        return self


class IngestResponse(BaseModel):
    symbol: str
    bars_ingested: int
    stored: bool
    quality_report: DataQualityReport


# Sync endpoint on purpose (ADR-009): FastAPI runs `def` handlers in a threadpool so the
# blocking yfinance fetch and DB writes don't stall the event loop.
@router.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
) -> IngestResponse:
    result = DataIngestionPipeline(adapter, repository).ingest(
        request.symbol, request.start_date, request.end_date
    )
    return IngestResponse(
        symbol=result.symbol,
        bars_ingested=result.bars_ingested,
        stored=result.stored,
        quality_report=result.quality_report,
    )
