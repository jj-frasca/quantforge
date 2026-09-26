from dataclasses import dataclass
from datetime import datetime

from app.data.models import DataQualityReport
from app.data.quality.engine import DataQualityEngine
from app.data.sources.base import DataSourceAdapter
from app.data.storage.repository import PriceBarRepository


@dataclass(frozen=True)
class IngestionResult:
    symbol: str
    bars_ingested: int
    stored: bool
    quality_report: DataQualityReport


def validate_ingestion_range(start: datetime, end: datetime) -> None:
    """Require one non-empty timezone-aware half-open acquisition interval."""
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start and end must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("start and end must be timezone-aware")
    if start >= end:
        raise ValueError("start must be before end")


class DataIngestionPipeline:
    """Adapter -> normalize (in adapter) -> quality gate -> store (ADR-006).

    Notes:
        The quality report is always persisted; the bars are stored only when the report
        passes the gate. A failing gate (e.g. unusable data) blocks storage rather than
        letting research run on it.
    """

    def __init__(
        self,
        adapter: DataSourceAdapter,
        repository: PriceBarRepository,
        quality_engine: DataQualityEngine | None = None,
    ) -> None:
        self._adapter = adapter
        self._repository = repository
        self._quality = quality_engine or DataQualityEngine()

    def ingest(self, symbol: str, start: datetime, end: datetime) -> IngestionResult:
        validate_ingestion_range(start, end)
        bars = self._adapter.fetch_price_bars(symbol, start, end)
        report = self._quality.check(
            bars,
            symbol,
            expected_source=self._adapter.source,
            expected_start=start,
            expected_end=end,
        )
        self._repository.save_quality_report(report)

        stored = report.passed
        if stored:
            self._repository.save_bars(bars)

        return IngestionResult(
            # Matches DataQualityEngine.check()'s own internal normalization (FINDING-054/ADR-126)
            # so IngestionResult.symbol always agrees with quality_report.symbol on the same result,
            # regardless of the raw request's casing/whitespace.
            symbol=symbol.strip().upper(),
            bars_ingested=len(bars),
            stored=stored,
            quality_report=report,
        )
