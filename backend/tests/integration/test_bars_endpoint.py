"""GET /api/v1/bars (integration): reads bars from the repo (does NOT trigger ingestion);
returns chart-shaped bars (floats, not Decimal); 200 with [] when nothing is cached."""

from fastapi.testclient import TestClient
from tests.fixtures.synthetic import builders

from app.data.storage.memory import InMemoryPriceBarRepository
from app.data.storage.repository import PriceBarRepository
from app.dependencies import get_repository
from app.main import app

_QUERY = {
    "symbol": "AAPL",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-01T00:00:00Z",
}


def _client(repo: PriceBarRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_bars_endpoint_returns_cached_bars_as_floats() -> None:
    try:
        repo = InMemoryPriceBarRepository()
        repo.save_bars(builders.clean_series(symbol="AAPL", n=10))
        response = _client(repo).get("/api/v1/bars", params=_QUERY)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["n_bars"] == 10
        assert len(body["bars"]) == 10
        first = body["bars"][0]
        assert set(first) == {"timestamp_utc", "open", "high", "low", "close", "volume"}
        # ChartBar values are JSON numbers, not Decimal strings
        assert isinstance(first["open"], float)
        assert isinstance(first["volume"], int)
    finally:
        app.dependency_overrides.clear()


def test_bars_endpoint_returns_empty_when_nothing_cached() -> None:
    try:
        response = _client(InMemoryPriceBarRepository()).get("/api/v1/bars", params=_QUERY)
        assert response.status_code == 200
        body = response.json()
        assert body["n_bars"] == 0
        assert body["bars"] == []
    finally:
        app.dependency_overrides.clear()


def test_bars_endpoint_returns_bars_sorted_by_timestamp() -> None:
    try:
        repo = InMemoryPriceBarRepository()
        repo.save_bars(builders.clean_series(symbol="AAPL", n=20))
        response = _client(repo).get("/api/v1/bars", params=_QUERY)
        timestamps = [bar["timestamp_utc"] for bar in response.json()["bars"]]
        assert timestamps == sorted(timestamps)
    finally:
        app.dependency_overrides.clear()
