from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.data.sources.base import DataSourceAdapter
from app.data.sources.yfinance import YFinanceAdapter
from app.data.storage.db import create_db_engine, create_session_factory
from app.data.storage.memory import InMemoryPriceBarRepository
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


@lru_cache
def _memory_repository() -> InMemoryPriceBarRepository:
    """Process-local singleton so cached bars survive across requests within one run."""
    return InMemoryPriceBarRepository()


def get_repository() -> PriceBarRepository:
    """FastAPI dependency for the PriceBarRepository.

    Notes:
        Returns an InMemoryPriceBarRepository when `storage_backend == "memory"` (the default
        — what makes standalone `uvicorn` work without Docker) or a
        TimescaleDBPriceBarRepository when `storage_backend == "timescale"` (production /
        docker-compose). The Timescale branch is `# pragma: no cover` because the unit test
        suite excludes DB-bound paths; integration tests cover it via `make test-integration`.
        Tests override this entirely via `app.dependency_overrides` so neither branch runs in
        `make test`.
    """
    if get_settings().storage_backend == "memory":
        return _memory_repository()
    return TimescaleDBPriceBarRepository(_session_factory())  # pragma: no cover - DB glue
