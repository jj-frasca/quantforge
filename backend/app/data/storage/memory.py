from datetime import datetime

from app.data.models import DataQualityReport, PriceBar, Source


class InMemoryPriceBarRepository:
    """In-memory PriceBarRepository for tests and local dev (no DB required).

    Implements the PriceBarRepository Protocol structurally. Not for production — the
    TimescaleDB-backed repository is the real store.
    """

    def __init__(self) -> None:
        self._bars: dict[str, dict[tuple[datetime, str], PriceBar]] = {}
        self._reports: list[DataQualityReport] = []

    def save_bars(self, bars: list[PriceBar]) -> int:
        validated = [PriceBar.model_validate(bar.model_dump(round_trip=True)) for bar in bars]
        # Keyed by (timestamp_utc, source) per symbol, mirroring the production repository's
        # (symbol, timestamp_utc, source) upsert PK (FINDING-050/ADR-122) — re-saving the same
        # bar (e.g. an overlapping-range cache-aside re-ingest) must overwrite, not duplicate.
        for bar in validated:
            self._bars.setdefault(bar.symbol, {})[(bar.timestamp_utc, bar.source)] = bar
        return len(validated)

    def save_quality_report(self, report: DataQualityReport) -> None:
        validated = DataQualityReport.model_validate(report.model_dump(round_trip=True))
        self._reports.append(validated)

    def get_bars(
        self, symbol: str, start: datetime, end: datetime, *, source: Source
    ) -> list[PriceBar]:
        bars = self._bars.get(symbol.strip().upper(), {}).values()
        return sorted(
            (b for b in bars if b.source == source and start <= b.timestamp_utc < end),
            key=lambda b: b.timestamp_utc,
        )

    @property
    def quality_reports(self) -> list[DataQualityReport]:
        return list(self._reports)
