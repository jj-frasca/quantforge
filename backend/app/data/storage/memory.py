from datetime import datetime

from app.data.models import DataQualityReport, PriceBar


class InMemoryPriceBarRepository:
    """In-memory PriceBarRepository for tests and local dev (no DB required).

    Implements the PriceBarRepository Protocol structurally. Not for production — the
    TimescaleDB-backed repository is the real store.
    """

    def __init__(self) -> None:
        self._bars: dict[str, list[PriceBar]] = {}
        self._reports: list[DataQualityReport] = []

    def save_bars(self, bars: list[PriceBar]) -> int:
        for bar in bars:
            self._bars.setdefault(bar.symbol, []).append(bar)
        return len(bars)

    def save_quality_report(self, report: DataQualityReport) -> None:
        self._reports.append(report)

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        bars = self._bars.get(symbol.strip().upper(), [])
        return sorted(
            (b for b in bars if start <= b.timestamp_utc < end),
            key=lambda b: b.timestamp_utc,
        )

    @property
    def quality_reports(self) -> list[DataQualityReport]:
        return list(self._reports)
