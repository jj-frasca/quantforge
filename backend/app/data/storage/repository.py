from datetime import datetime
from typing import Protocol

from app.data.models import DataQualityReport, PriceBar


class PriceBarRepository(Protocol):
    """Storage contract for canonical price bars and their quality reports.

    Keeps the ingestion pipeline independent of the concrete store (in-memory for tests/dev,
    TimescaleDB in production). Reads always take a symbol AND a time range (ADR-003).
    """

    def save_bars(self, bars: list[PriceBar]) -> int:
        """Persist bars; return the number stored."""
        ...

    def save_quality_report(self, report: DataQualityReport) -> None:
        """Persist a quality report (kept even when its data is gated out)."""
        ...

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        """Return stored bars for ``symbol`` in the half-open range ``[start, end)``."""
        ...
