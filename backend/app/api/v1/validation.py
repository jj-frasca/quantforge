from datetime import datetime
from typing import Annotated, Self

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator

from app.api.v1.backtest import _MIN_BARS, _load_frame
from app.data.pipelines.ingestion import validate_request_range
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.research.strategies.grid_generator import find_catalog_entry, grid_from_catalog
from app.validation.engine import ValidationEngine
from app.validation.report import ValidationReport

router = APIRouter(tags=["validation"])

_MIN_CONFIGS_FOR_PBO = 2  # CSCV needs at least 2 valid configs to estimate overfitting


class ValidateRequest(BaseModel):
    symbol: str
    # Any catalog name — backend validates against STRATEGY_CATALOG; an unknown name 422s.
    # The catalog is the single source of truth for the supported set (ADR-010).
    strategy: str
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        validate_request_range(self.start_date, self.end_date)
        return self


# Sync endpoint on purpose: FastAPI runs `def` handlers in a threadpool, so the blocking
# yfinance fetch and DB calls don't stall the event loop (ADR-009 sync stack).
@router.post("/validate", response_model=ValidationReport)
def validate(
    request: ValidateRequest,
    adapter: Annotated[DataSourceAdapter, Depends(get_data_adapter)],
    repository: Annotated[PriceBarRepository, Depends(get_repository)],
) -> ValidationReport:
    catalog_entry = find_catalog_entry(request.strategy)
    if catalog_entry is None:
        raise HTTPException(
            status_code=422,
            detail=f"unknown strategy: {request.strategy!r}; see GET /api/v1/strategies",
        )

    frame = _load_frame(request.symbol, request.start_date, request.end_date, adapter, repository)
    if len(frame) < _MIN_BARS:
        raise HTTPException(
            status_code=422,
            detail=f"insufficient data: {len(frame)} bars (need >= {_MIN_BARS})",
        )

    # Catalog-driven grid (ADR-010 §Consequences). Hand-curated grids drift the moment a
    # new strategy lands; deriving the grid from the catalog's param schema keeps validation
    # parity with /backtest automatically.
    configs = grid_from_catalog(catalog_entry, n_per_param=3)
    if len(configs) < _MIN_CONFIGS_FOR_PBO:  # pragma: no cover
        # Defensive: tests/unit/test_grid_generator.py asserts every catalog entry
        # currently in STRATEGY_CATALOG produces >= 2 valid configs at n_per_param=3.
        # This branch is the runtime backstop if a future catalog edit narrows bounds
        # too aggressively (e.g., min == max on every param).
        raise HTTPException(
            status_code=422,
            detail=(
                f"catalog grid produced only {len(configs)} valid configs for "
                f"{request.strategy!r}; need >= {_MIN_CONFIGS_FOR_PBO} for PBO"
            ),
        )
    return ValidationEngine().validate(request.strategy, configs, frame)
