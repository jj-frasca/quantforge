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
        bars = self._adapter.fetch_price_bars(symbol, start, end)
        report = self._quality.check(bars, symbol)
        self._repository.save_quality_report(report)

        stored = report.passed
        if stored:
            self._repository.save_bars(bars)

        return IngestionResult(
            symbol=symbol,
            bars_ingested=len(bars),
            stored=stored,
            quality_report=report,
        )
