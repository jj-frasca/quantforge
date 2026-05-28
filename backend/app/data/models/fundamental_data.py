from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.data.models.types import Source


class FundamentalData(BaseModel):
    """Point-in-time fundamentals for one symbol (data-contracts.md §3).

    Notes:
        Ratios are nullable on purpose — missing/undefined is common and must never be
        coerced to 0. net_income and the ratios may be negative; only market_cap is
        constrained (> 0 when present).
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    report_date: date
    pe_ratio: Decimal | None = None
    pb_ratio: Decimal | None = None
    ps_ratio: Decimal | None = None
    ev_ebitda: Decimal | None = None
    revenue: Decimal | None = None
    net_income: Decimal | None = None
    market_cap: Decimal | None = None
    sector: str | None = None
    industry: str | None = None
    source: Source

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @field_validator("market_cap")
    @classmethod
    def _market_cap_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("market_cap must be > 0 when present")
        return v
