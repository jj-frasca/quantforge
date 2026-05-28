from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models (data-contracts.md §6)."""


class PriceBarORM(Base):
    __tablename__ = "price_bars"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger)
    adj_factor: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    source: Mapped[str] = mapped_column(String, primary_key=True)
    quality_flags: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class FundamentalORM(Base):
    __tablename__ = "fundamentals"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ps_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    net_income: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)


class DataQualityReportORM(Base):
    __tablename__ = "data_quality_reports"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    symbol: Mapped[str] = mapped_column(String)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    passed: Mapped[bool] = mapped_column(Boolean)
    issues: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
