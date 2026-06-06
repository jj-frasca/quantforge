"""POST /api/v1/validate (integration, cache-aside): cache miss → ingest pipeline runs;
cache hit → adapter is NOT called; 422 on unknown strategy or insufficient data."""

from datetime import datetime

import pytest
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
    "strategy": "sma",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-01T00:00:00Z",
}


class _FakeAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "fake-1"

    def __init__(self, n: int = 300) -> None:
        self._n = n
        self.calls = 0

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        self.calls += 1
        return builders.clean_series(symbol=symbol, n=self._n)


class _BoomAdapter(DataSourceAdapter):
    """Adapter that fails if called — proves the cache-hit path doesn't hit the network."""

    source = "yfinance"
    adapter_version = "fake-boom"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raise AssertionError("adapter should not be called on cache hit")


def _client(adapter: DataSourceAdapter, repo: PriceBarRepository) -> TestClient:
    app.dependency_overrides[get_data_adapter] = lambda: adapter
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


@pytest.mark.parametrize(
    "strategy",
    [
        # Every catalog strategy must validate end-to-end via the catalog-driven grid
        # (ADR-010 §Consequences). The list of catalog names lives in catalog.py; if a
        # new one lands without the auto-generated grid producing enough valid configs,
        # this parametrize will surface it explicitly.
        "sma",
        "momentum",
        "mean_reversion",
        "rsi_mean_reversion",
        "donchian_breakout",
        "bollinger_bands",
        "macd_crossover",
        "vol_targeted_sma",
        "keltner_channel",
        "trend_filtered_mean_reversion",
        "triple_ma_alignment",
    ],
)
def test_validate_endpoint_on_cache_miss_ingests_then_validates(strategy: str) -> None:
    try:
        adapter, repo = _FakeAdapter(), InMemoryPriceBarRepository()
        response = _client(adapter, repo).post(
            "/api/v1/validate", json={**_BODY, "strategy": strategy}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["strategy_name"] == strategy
        assert 0.0 <= body["pbo"] <= 1.0
        assert "passed" in body
        assert "parameter_stability_score" in body
        # cache miss invoked the ingestion pipeline exactly once
        assert adapter.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_validate_endpoint_on_cache_hit_does_not_call_adapter() -> None:
    try:
        repo = InMemoryPriceBarRepository()
        repo.save_bars(builders.clean_series(n=300))  # pre-warm the cache
        response = _client(_BoomAdapter(), repo).post("/api/v1/validate", json=_BODY)
        assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.clear()


def test_validate_endpoint_rejects_unknown_strategy() -> None:
    response = TestClient(app).post("/api/v1/validate", json={**_BODY, "strategy": "bogus"})
    assert response.status_code == 422


def test_validate_endpoint_rejects_insufficient_data() -> None:
    # Cache miss + adapter returns too few bars → quality gate fails OR frame too small;
    # either way the endpoint must reject with 422 (frame check is the backstop).
    try:
        response = _client(_FakeAdapter(n=10), InMemoryPriceBarRepository()).post(
            "/api/v1/validate", json=_BODY
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
