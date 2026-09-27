"""Every public range-bearing API rejects malformed intervals before data access."""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.data.models import PriceBar, Source
from app.data.sources.base import DataSourceAdapter
from app.data.storage.memory import InMemoryPriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.main import app


class _FailIfCalledAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "test-1"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raise AssertionError("invalid range reached the adapter")


class _FailIfAccessedRepository(InMemoryPriceBarRepository):
    def get_bars(
        self, symbol: str, start: datetime, end: datetime, *, source: Source
    ) -> list[PriceBar]:
        raise AssertionError("invalid range reached the repository")


_STRATEGY = {"name": "sma", "fast": 5, "slow": 20}
_POST_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("/api/v1/backtest", {"symbol": "AAPL", "strategy": _STRATEGY}),
    ("/api/v1/validate", {"symbol": "AAPL", "strategy": "sma"}),
    ("/api/v1/monte-carlo", {"symbol": "AAPL", "strategy": _STRATEGY}),
)
_INVALID_RANGES = (
    ("2024-01-01T00:00:00", "2024-12-01T00:00:00Z"),
    ("2024-01-01T00:00:00Z", "2024-12-01T00:00:00"),
    ("2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"),
    ("2024-12-01T00:00:00Z", "2024-01-01T00:00:00Z"),
)


@pytest.mark.parametrize(("path", "body"), _POST_CASES)
@pytest.mark.parametrize(("start_date", "end_date"), _INVALID_RANGES)
def test_research_post_rejects_invalid_range_before_data_access(
    path: str,
    body: dict[str, Any],
    start_date: str,
    end_date: str,
) -> None:
    app.dependency_overrides[get_data_adapter] = lambda: _FailIfCalledAdapter()
    app.dependency_overrides[get_repository] = lambda: _FailIfAccessedRepository()
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            path,
            json={**body, "start_date": start_date, "end_date": end_date},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(("start_date", "end_date"), _INVALID_RANGES)
def test_bars_rejects_invalid_range_before_repository_access(
    start_date: str,
    end_date: str,
) -> None:
    app.dependency_overrides[get_repository] = lambda: _FailIfAccessedRepository()
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/v1/bars",
            params={"symbol": "AAPL", "start_date": start_date, "end_date": end_date},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
