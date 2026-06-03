"""POST /api/v1/backtest (integration, cache-aside): runs a single backtest of the chosen
strategy+params and returns the equity curve + metrics; 422 on insufficient data;
unknown strategy name fails Pydantic validation."""

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


def _client(adapter: DataSourceAdapter, repo: PriceBarRepository) -> TestClient:
    app.dependency_overrides[get_data_adapter] = lambda: adapter
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def test_backtest_endpoint_returns_equity_curve_and_metrics() -> None:
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["strategy_name"] == "sma_crossover"
        assert body["parameters"] == {"fast": 5, "slow": 20}
        assert "metrics" in body
        assert "sharpe" in body["metrics"]
        assert len(body["equity_curve"]) > 0
        first = body["equity_curve"][0]
        assert set(first) == {"timestamp_utc", "equity"}
        assert isinstance(first["equity"], float)
        # Buy-and-hold reference is the same length as the strategy curve
        assert len(body["buy_and_hold_curve"]) == len(body["equity_curve"])
        assert isinstance(body["buy_and_hold_total_return"], float)
        # Drawdown is in [-1, 0] and same length as the equity curve
        assert len(body["drawdown_curve"]) == len(body["equity_curve"])
        for point in body["drawdown_curve"]:
            assert -1.0 <= point["drawdown"] <= 0.0
        # Rolling Sharpe shares the same length; the window is exposed; warmup is 0.0
        assert len(body["rolling_sharpe_curve"]) == len(body["equity_curve"])
        assert body["rolling_sharpe_window"] == 60
        assert body["rolling_sharpe_curve"][0]["sharpe"] == 0.0
        # Return distribution has the configured bin count + skew + excess kurtosis
        dist = body["return_distribution"]
        assert len(dist["bins"]) == 30
        assert sum(b["frequency"] for b in dist["bins"]) == len(body["equity_curve"])
        assert isinstance(dist["skewness"], float)
        assert isinstance(dist["kurtosis"], float)
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_momentum() -> None:
    body = {**_BODY, "strategy": {"name": "momentum", "lookback": 30, "skip": 2}}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "momentum"
        assert result["parameters"] == {"lookback": 30, "skip": 2}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_mean_reversion() -> None:
    body = {**_BODY, "strategy": {"name": "mean_reversion", "window": 20, "k": 1.5}}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "mean_reversion"
        assert result["parameters"] == {"window": 20, "k": 1.5}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_rsi_mean_reversion() -> None:
    body = {
        **_BODY,
        "strategy": {
            "name": "rsi_mean_reversion",
            "window": 10,
            "oversold": 25,
            "overbought": 75,
        },
    }
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "rsi_mean_reversion"
        assert result["parameters"] == {"window": 10, "oversold": 25, "overbought": 75}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_donchian_breakout() -> None:
    body = {**_BODY, "strategy": {"name": "donchian_breakout", "lookback": 15}}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "donchian_breakout"
        assert result["parameters"] == {"lookback": 15}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_bollinger_bands() -> None:
    body = {**_BODY, "strategy": {"name": "bollinger_bands", "window": 15, "num_std": 1.5}}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "bollinger_bands"
        assert result["parameters"] == {"window": 15, "num_std": 1.5}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_macd_crossover() -> None:
    body = {**_BODY, "strategy": {"name": "macd_crossover", "fast": 8, "slow": 21, "signal": 5}}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "macd_crossover"
        assert result["parameters"] == {"fast": 8, "slow": 21, "signal": 5}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_rejects_unknown_strategy_name() -> None:
    # discriminated union: an unknown `name` is a 422 from Pydantic, never reaches our handler
    bad = {**_BODY, "strategy": {"name": "bogus", "fast": 5, "slow": 20}}
    response = TestClient(app).post("/api/v1/backtest", json=bad)
    assert response.status_code == 422


def test_backtest_endpoint_rejects_insufficient_data() -> None:
    try:
        response = _client(_FakeAdapter(n=10), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
