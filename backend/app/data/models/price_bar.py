from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.data.models.types import Source


class PriceBar(BaseModel):
    """Canonical OHLCV bar (ADR-004). Split/dividend-adjusted, normalized at ingestion.

    Notes:
        timestamp_utc is enforced UTC (ADR-006): a naive datetime is rejected rather than
        silently assumed-local. adj_factor is already applied to OHLC — applying it again
        downstream makes prices adj_factor x wrong.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_factor: Decimal
    source: Source
    quality_flags: dict[str, object] | None = None

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @field_validator("timestamp_utc")
    @classmethod
    def _coerce_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware UTC; naive datetime rejected")
        return v.astimezone(UTC)

    @field_validator("open", "high", "low", "close", "adj_factor")
    @classmethod
    def _positive(cls, v: Decimal) -> Decimal:
        # Pydantic's Decimal already rejects NaN/Inf (allow_inf_nan=False by default).
        if v <= 0:
            raise ValueError("must be > 0")
        return v

    @field_validator("volume")
    @classmethod
    def _non_negative_volume(cls, v: int) -> int:
        if v < 0:
            raise ValueError("volume must be >= 0")
        return v

    @model_validator(mode="after")
    def _check_ohlc_ordering(self) -> Self:
        body_low = min(self.open, self.close)
        body_high = max(self.open, self.close)
        if self.low > body_low:
            raise ValueError("low must be <= min(open, close)")
        if self.high < body_high:
            raise ValueError("high must be >= max(open, close)")
        return self
