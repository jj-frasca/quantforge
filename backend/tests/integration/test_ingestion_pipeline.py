"""DataIngestionPipeline (integration): a clean series ingests end-to-end and is queryable back; a failing quality gate blocks storage but still persists the report."""

from datetime import UTC, datetime

from tests.fixtures.synthetic import builders

from app.data.models import PriceBar
from app.data.pipelines.ingestion import DataIngestionPipeline
from app.data.sources.base import DataSourceAdapter
from app.data.storage.memory import InMemoryPriceBarRepository

_START = datetime(2024, 1, 1, tzinfo=UTC)
_END = datetime(2024, 3, 1, tzinfo=UTC)


class _SeriesAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "test-1"

    def __init__(self, bars: list[PriceBar]) -> None:
        self._bars = bars

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        return self._bars


def test_pipeline_ingests_clean_series_end_to_end() -> None:
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(builders.clean_series(n=30)), repo)

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is True
    assert result.bars_ingested == 30
    assert result.quality_report.passed is True
    # query back via the mandatory (symbol + range) pattern
    assert len(repo.get_bars("AAPL", _START, _END)) == 30
    assert len(repo.quality_reports) == 1


def test_pipeline_blocks_storage_when_quality_gate_fails() -> None:
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter([]), repo)  # empty -> insufficient_data error

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is False
    assert result.quality_report.passed is False
    assert repo.get_bars("AAPL", _START, _END) == []
    # the report is still persisted even though the bars are not
    assert len(repo.quality_reports) == 1
