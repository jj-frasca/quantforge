from datetime import UTC, datetime

from tests.fixtures.synthetic import builders

from app.data.models import DataQualityReport
from app.data.storage.memory import InMemoryPriceBarRepository


def test_save_bars_returns_count_and_get_bars_returns_them() -> None:
    repo = InMemoryPriceBarRepository()
    bars = builders.clean_series(n=10)
    assert repo.save_bars(bars) == 10
    back = repo.get_bars("AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC))
    assert len(back) == 10


def test_get_bars_filters_by_symbol() -> None:
    repo = InMemoryPriceBarRepository()
    repo.save_bars(builders.clean_series(symbol="AAPL", n=5))
    out = repo.get_bars("MSFT", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC))
    assert out == []


def test_get_bars_respects_half_open_range() -> None:
    repo = InMemoryPriceBarRepository()
    bars = builders.clean_series(n=10)
    repo.save_bars(bars)
    # range ending exactly at the first bar's timestamp excludes it (half-open)
    first_ts = bars[0].timestamp_utc
    out = repo.get_bars("AAPL", datetime(2023, 1, 1, tzinfo=UTC), first_ts)
    assert out == []


def test_save_quality_report_is_retained() -> None:
    repo = InMemoryPriceBarRepository()
    report = DataQualityReport(symbol="AAPL", checked_at=datetime(2024, 1, 2, tzinfo=UTC))
    repo.save_quality_report(report)
    assert repo.quality_reports == [report]
