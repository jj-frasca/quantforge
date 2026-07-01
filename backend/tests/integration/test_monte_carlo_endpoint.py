"""POST /api/v1/monte-carlo (ADR-014 Phase 0): runs the requested strategy, then Monte-Carlo
simulates its forward risk over a horizon. Deterministic under the request seed; a benchmark
risk tool for the StrategyLab gate, not a prediction."""

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
    "strategy": {"name": "sma", "fast": 5, "slow": 20},
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2024-12-01T00:00:00Z",
    "horizon_days": 126,
    "n_paths": 4000,
    "loss_threshold": 0.2,
    "seed": 42,
}

_KEYS = {
    "symbol",
    "strategy_name",
    "parameters",
    "horizon_days",
    "n_paths",
    "loss_threshold",
    "prob_terminal_loss",
    "prob_max_drawdown_exceeds",
    "terminal_return_p5",
    "terminal_return_p50",
    "terminal_return_p95",
    "expected_terminal_return",
}


class _FakeAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "fake-1"

    def __init__(self, n: int = 400) -> None:
        self._n = n

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        return builders.clean_series(symbol=symbol, n=self._n)


def _client(adapter: DataSourceAdapter, repo: PriceBarRepository) -> TestClient:
    app.dependency_overrides[get_data_adapter] = lambda: adapter
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_monte_carlo_endpoint_returns_risk_summary() -> None:
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/monte-carlo", json=_BODY
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == _KEYS
        assert body["symbol"] == "AAPL"
        assert body["strategy_name"] == "sma_crossover"
        assert body["horizon_days"] == 126
        assert body["n_paths"] == 4000
        assert 0.0 <= body["prob_terminal_loss"] <= 1.0
        assert 0.0 <= body["prob_max_drawdown_exceeds"] <= 1.0
        assert (
            body["terminal_return_p5"] <= body["terminal_return_p50"] <= body["terminal_return_p95"]
        )
    finally:
        app.dependency_overrides.clear()


def test_monte_carlo_endpoint_is_deterministic_under_seed() -> None:
    try:
        client = _client(_FakeAdapter(), InMemoryPriceBarRepository())
        first = client.post("/api/v1/monte-carlo", json=_BODY).json()
        second = client.post("/api/v1/monte-carlo", json=_BODY).json()
        assert first == second
    finally:
        app.dependency_overrides.clear()


def test_monte_carlo_endpoint_rejects_out_of_range_loss_threshold() -> None:
    response = TestClient(app).post("/api/v1/monte-carlo", json={**_BODY, "loss_threshold": 0})
    assert response.status_code == 422


def test_monte_carlo_endpoint_rejects_insufficient_data() -> None:
    try:
        response = _client(_FakeAdapter(n=10), InMemoryPriceBarRepository()).post(
            "/api/v1/monte-carlo", json=_BODY
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
