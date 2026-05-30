from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.data.sources.base import DataSourceAdapter
from app.data.sources.yfinance import YFinanceAdapter
from app.data.storage.db import create_db_engine, create_session_factory
from app.data.storage.repository import PriceBarRepository
from app.data.storage.timescale import TimescaleDBPriceBarRepository


def get_data_adapter() -> DataSourceAdapter:
    """FastAPI dependency for the market-data adapter (yfinance by default).

    Overridden in tests via app.dependency_overrides to inject synthetic data.
    """
    return YFinanceAdapter()


@lru_cache
def _session_factory() -> sessionmaker[Session]:  # pragma: no cover - DB glue (integration tests)
    return create_session_factory(create_db_engine())


def get_repository() -> PriceBarRepository:  # pragma: no cover - DB glue (integration tests)
    """FastAPI dependency for the PriceBarRepository (TimescaleDB sync, ADR-009).

    Overridden in tests with an InMemoryPriceBarRepository via app.dependency_overrides — the
    real engine is never built during `make test`.
    """
    return TimescaleDBPriceBarRepository(_session_factory())
