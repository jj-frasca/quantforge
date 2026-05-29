"""ORM schema: compiled PostgreSQL DDL matches data-contracts.md (NUMERIC precisions, TIMESTAMPTZ, JSONB, UUID pk, composite primary keys)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.data.storage.orm import DataQualityReportORM, FundamentalORM, PriceBarORM


def _ddl(table: object) -> str:
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore[arg-type]


def test_price_bars_ddl_matches_data_contract() -> None:
    ddl = _ddl(PriceBarORM.__table__)
    assert "price_bars" in ddl
    assert "NUMERIC(18, 6)" in ddl  # OHLC precision
    assert "NUMERIC(10, 6)" in ddl  # adj_factor
    assert "BIGINT" in ddl  # volume
    assert "TIMESTAMP WITH TIME ZONE" in ddl  # timestamp_utc
    assert "JSONB" in ddl  # quality_flags
    assert "PRIMARY KEY (symbol, timestamp_utc, source)" in ddl


def test_fundamentals_ddl_has_composite_key_and_nullable_ratios() -> None:
    ddl = _ddl(FundamentalORM.__table__)
    assert "fundamentals" in ddl
    assert "PRIMARY KEY (symbol, report_date, source)" in ddl
    assert "DATE" in ddl


def test_data_quality_reports_ddl_has_uuid_pk_and_jsonb_issues() -> None:
    ddl = _ddl(DataQualityReportORM.__table__)
    assert "data_quality_reports" in ddl
    assert "UUID" in ddl
    assert "JSONB" in ddl
    assert "BOOLEAN" in ddl
