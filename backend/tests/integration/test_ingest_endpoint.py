"""POST /api/v1/ingest (integration): runs the ingestion pipeline, returns the
quality report. Clean data -> stored=True, passed=True; insufficient data -> stored=False."""

from datetime import datetime

from fastapi.testclient import TestClient
from tests.fixtures.synthetic import builders

from app.data.models import PriceBar
from app.data.sources.base import DataSourceAdapter
from app.data.storage.memory import InMemoryPriceBarRepository
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_data_adapter, get_repository
from app.main import app

_BODY = {
    "symbol": "AAPL",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-01T00:00:00Z",
}


class _SeriesAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "fake-1"

    def __init__(self, bars: list[PriceBar]) -> None:
        self._bars = bars

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        return self._bars


def _client(adapter: DataSourceAdapter, repo: PriceBarRepository) -> TestClient:
    app.dependency_overrides[get_data_adapter] = lambda: adapter
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_ingest_stores_bars_and_returns_a_passing_report() -> None:
    try:
        repo = InMemoryPriceBarRepository()
        adapter = _SeriesAdapter(builders.clean_series(n=30))
        response = _client(adapter, repo).post("/api/v1/ingest", json=_BODY)
        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["bars_ingested"] == 30
        assert body["stored"] is True
        assert body["quality_report"]["passed"] is True
        # bars are queryable back through the repo
        assert (
            len(
                repo.get_bars(
                    "AAPL",
                    datetime.fromisoformat(_BODY["start_date"].replace("Z", "+00:00")),
                    datetime.fromisoformat(_BODY["end_date"].replace("Z", "+00:00")),
                )
            )
            == 30
        )
    finally:
        app.dependency_overrides.clear()


def test_ingest_does_not_store_when_quality_gate_fails() -> None:
    try:
        repo = InMemoryPriceBarRepository()
        response = _client(_SeriesAdapter([]), repo).post("/api/v1/ingest", json=_BODY)
        assert response.status_code == 200
        body = response.json()
        assert body["stored"] is False
        assert body["quality_report"]["passed"] is False
    finally:
        app.dependency_overrides.clear()
