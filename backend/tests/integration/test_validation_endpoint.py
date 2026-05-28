from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.synthetic import builders

from app.data.models import PriceBar
from app.data.sources.base import DataSourceAdapter
from app.dependencies import get_data_adapter
from app.main import app

_BODY = {
    "symbol": "AAPL",
    "strategy": "sma",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-01T00:00:00Z",
}


class _FakeAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "fake-1"

    def __init__(self, n: int = 300) -> None:
        self._n = n

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        return builders.clean_series(symbol=symbol, n=self._n)


def _client(adapter: DataSourceAdapter) -> TestClient:
    app.dependency_overrides[get_data_adapter] = lambda: adapter
    return TestClient(app)


@pytest.mark.parametrize("strategy", ["sma", "momentum", "mean_reversion"])
def test_validate_endpoint_returns_a_report(strategy: str) -> None:
    try:
        response = _client(_FakeAdapter()).post(
            "/api/v1/validate", json={**_BODY, "strategy": strategy}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["strategy_name"] == strategy
        assert 0.0 <= body["pbo"] <= 1.0
        assert "passed" in body
        assert "parameter_stability_score" in body
    finally:
        app.dependency_overrides.clear()


def test_validate_endpoint_rejects_unknown_strategy() -> None:
    response = TestClient(app).post("/api/v1/validate", json={**_BODY, "strategy": "bogus"})
    assert response.status_code == 422


def test_validate_endpoint_rejects_insufficient_data() -> None:
    try:
        response = _client(_FakeAdapter(n=10)).post("/api/v1/validate", json=_BODY)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
