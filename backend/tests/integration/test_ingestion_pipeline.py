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


def test_pipeline_result_symbol_matches_the_normalized_quality_report_symbol() -> None:
    # FINDING-054/ADR-126: DataQualityEngine.check() normalizes (strip+upper) internally and
    # stamps that onto DataQualityReport.symbol, but IngestionResult.symbol carried the raw,
    # unnormalized input — for a lowercase/whitespace request, the two symbol fields on one
    # response disagreed in case, and neither matched what GET /bars (which normalizes its own
    # response) would echo back for the same symbol.
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(builders.clean_series(n=30)), repo)

    result = pipeline.ingest("  aapl  ", _START, _END)

    assert result.symbol == "AAPL"
    assert result.symbol == result.quality_report.symbol


def test_pipeline_blocks_storage_when_quality_gate_fails() -> None:
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter([]), repo)  # empty -> insufficient_data error

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is False
    assert result.quality_report.passed is False
    assert repo.get_bars("AAPL", _START, _END) == []
    # the report is still persisted even though the bars are not
    assert len(repo.quality_reports) == 1


def test_pipeline_blocks_mislabeled_adapter_series() -> None:
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(builders.clean_series(symbol="AAPL")), repo)

    result = pipeline.ingest("MSFT", _START, _END)

    assert result.stored is False
    assert result.quality_report.passed is False
    assert {issue.check for issue in result.quality_report.issues} == {"symbol_mismatch"}
    assert repo.get_bars("AAPL", _START, _END) == []
    assert len(repo.quality_reports) == 1


def test_pipeline_blocks_duplicate_calendar_rows() -> None:
    bars = builders.clean_series(symbol="AAPL")
    bars[1] = bars[1].model_copy(update={"timestamp_utc": bars[0].timestamp_utc})
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(bars), repo)

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is False
    assert {issue.check for issue in result.quality_report.issues} == {"duplicate_timestamp"}
    assert repo.get_bars("AAPL", _START, _END) == []
    assert len(repo.quality_reports) == 1


def test_pipeline_blocks_bars_from_a_different_source_than_adapter() -> None:
    bars = [
        bar.model_copy(update={"source": "alpaca"}) for bar in builders.clean_series(symbol="AAPL")
    ]
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(bars), repo)

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is False
    assert {issue.check for issue in result.quality_report.issues} == {"source_mismatch"}
    assert repo.get_bars("AAPL", _START, _END) == []
    assert len(repo.quality_reports) == 1


def test_pipeline_blocks_bars_outside_requested_half_open_range() -> None:
    bars = builders.clean_series(symbol="AAPL")
    bars[0] = bars[0].model_copy(update={"timestamp_utc": datetime(2023, 12, 31, tzinfo=UTC)})
    bars[-1] = bars[-1].model_copy(update={"timestamp_utc": _END})
    repo = InMemoryPriceBarRepository()
    pipeline = DataIngestionPipeline(_SeriesAdapter(bars), repo)

    result = pipeline.ingest("AAPL", _START, _END)

    assert result.stored is False
    assert {issue.check for issue in result.quality_report.issues} == {"range_mismatch"}
    assert repo.get_bars("AAPL", datetime(2023, 1, 1, tzinfo=UTC), _END) == []
    assert len(repo.quality_reports) == 1
