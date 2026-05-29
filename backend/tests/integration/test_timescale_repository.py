"""TimescaleDBPriceBarRepository (integration, needs Docker): round-trip, symbol+range
filtering, idempotent upsert, and quality-report persistence against real TimescaleDB."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.fixtures.synthetic import builders

from app.data.models import DataQualityReport
from app.data.storage.orm import DataQualityReportORM
from app.data.storage.timescale import TimescaleDBPriceBarRepository

pytestmark = pytest.mark.integration

_START = datetime(2024, 1, 1, tzinfo=UTC)
_END = datetime(2024, 3, 1, tzinfo=UTC)


def test_save_and_get_bars_round_trip(session_factory: sessionmaker[Session]) -> None:
    repo = TimescaleDBPriceBarRepository(session_factory)
    bars = builders.clean_series(n=20)

    assert repo.save_bars(bars) == 20
    fetched = repo.get_bars("AAPL", _START, _END)

    assert len(fetched) == 20
    assert [b.timestamp_utc for b in fetched] == sorted(b.timestamp_utc for b in fetched)
    assert fetched[0].close == bars[0].close  # Decimal preserved through NUMERIC


def test_get_bars_filters_by_symbol_and_half_open_range(
    session_factory: sessionmaker[Session],
) -> None:
    repo = TimescaleDBPriceBarRepository(session_factory)
    bars = builders.clean_series(n=10)
    repo.save_bars(bars)

    assert repo.get_bars("MSFT", _START, _END) == []  # wrong symbol
    # range ending exactly at the first bar excludes it (half-open)
    assert repo.get_bars("AAPL", datetime(2023, 1, 1, tzinfo=UTC), bars[0].timestamp_utc) == []


def test_save_bars_is_idempotent(session_factory: sessionmaker[Session]) -> None:
    repo = TimescaleDBPriceBarRepository(session_factory)
    bars = builders.clean_series(n=10)
    repo.save_bars(bars)
    repo.save_bars(bars)  # merge upserts on (symbol, timestamp_utc, source)
    assert len(repo.get_bars("AAPL", _START, _END)) == 10


def test_save_quality_report_persists(session_factory: sessionmaker[Session]) -> None:
    repo = TimescaleDBPriceBarRepository(session_factory)
    repo.save_quality_report(
        DataQualityReport(symbol="AAPL", checked_at=datetime(2024, 1, 2, tzinfo=UTC))
    )
    with session_factory() as session:
        count = session.execute(select(func.count()).select_from(DataQualityReportORM)).scalar_one()
    assert count == 1
