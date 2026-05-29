from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.data.models import DataQualityReport, PriceBar
from app.data.storage.orm import DataQualityReportORM, PriceBarORM


class TimescaleDBPriceBarRepository:
    """TimescaleDB-backed PriceBarRepository (sync, psycopg3 — ADR-009).

    Implements the same sync `PriceBarRepository` Protocol as the in-memory repo, so the
    ingestion pipeline is unchanged. Reads always filter by symbol AND a half-open time range
    (data-contracts.md §7) to hit the hypertable index instead of a full scan.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_bars(self, bars: list[PriceBar]) -> int:
        with self._session_factory() as session:
            for bar in bars:
                # merge = upsert by PK (symbol, timestamp_utc, source) -> idempotent ingestion
                session.merge(_to_orm(bar))
            session.commit()
        return len(bars)

    def save_quality_report(self, report: DataQualityReport) -> None:
        with self._session_factory() as session:
            session.add(
                DataQualityReportORM(
                    id=uuid4(),
                    symbol=report.symbol,
                    checked_at=report.checked_at,
                    passed=report.passed,
                    issues=[issue.model_dump() for issue in report.issues],
                )
            )
            session.commit()

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        stmt = (
            select(PriceBarORM)
            .where(
                PriceBarORM.symbol == symbol.strip().upper(),
                PriceBarORM.timestamp_utc >= start,
                PriceBarORM.timestamp_utc < end,
            )
            .order_by(PriceBarORM.timestamp_utc)
        )
        with self._session_factory() as session:
            return [_to_model(row) for row in session.execute(stmt).scalars()]


def _to_orm(bar: PriceBar) -> PriceBarORM:
    return PriceBarORM(
        symbol=bar.symbol,
        timestamp_utc=bar.timestamp_utc,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        adj_factor=bar.adj_factor,
        source=bar.source,
        quality_flags=bar.quality_flags,
    )


def _to_model(row: PriceBarORM) -> PriceBar:
    return PriceBar(
        symbol=row.symbol,
        timestamp_utc=row.timestamp_utc,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        adj_factor=row.adj_factor,
        source=row.source,  # type: ignore[arg-type]
        quality_flags=row.quality_flags,
    )
