"""POST /api/v1/backtest (integration, cache-aside): runs a single backtest of the chosen
strategy+params and returns the equity curve + metrics; 422 on insufficient data;
unknown strategy name fails Pydantic validation."""

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
        # Trade markers: present, shape is correct, every direction is buy or sell.
        # On a clean synthetic series with an SMA crossover, we expect at least one
        # signal flip past the warmup window — so the list is non-empty here.
        assert "trade_markers" in body
        assert isinstance(body["trade_markers"], list)
        assert len(body["trade_markers"]) > 0
        for marker in body["trade_markers"]:
            assert set(marker) == {"timestamp_utc", "direction", "equity"}
            assert marker["direction"] in {"buy", "sell"}
            assert isinstance(marker["equity"], float)
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


def test_backtest_endpoint_supports_vol_targeted_sma() -> None:
    body = {
        **_BODY,
        "strategy": {
            "name": "vol_targeted_sma",
            "fast": 10,
            "slow": 30,
            "vol_window": 20,
            "target_vol": 0.10,
        },
    }
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "vol_targeted_sma"
        assert result["parameters"] == {
            "fast": 10,
            "slow": 30,
            "vol_window": 20,
            "target_vol": 0.10,
        }
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_keltner_channel() -> None:
    body = {
        **_BODY,
        "strategy": {
            "name": "keltner_channel",
            "ma_window": 15,
            "atr_window": 10,
            "multiplier": 1.5,
        },
    }
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "keltner_channel"
        assert result["parameters"] == {"ma_window": 15, "atr_window": 10, "multiplier": 1.5}
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_supports_trend_filtered_mean_reversion() -> None:
    body = {
        **_BODY,
        "strategy": {
            "name": "trend_filtered_mean_reversion",
            "z_window": 15,
            "z_threshold": 1.2,
            "trend_window": 80,
        },
    }
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "trend_filtered_mean_reversion"
        assert result["parameters"] == {
            "z_window": 15,
            "z_threshold": 1.2,
            "trend_window": 80,
        }
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_defaults_initial_capital_and_cost_rate() -> None:
    # Omitted-by-caller path: engine defaults flow through. Documents the contract on
    # the existing _BODY shape so subsequent override tests have a baseline to compare to.
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["cost_rate"] == 0.001
        assert body["equity_curve"][0]["equity"] == pytest.approx(100_000.0, rel=1e-3)
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_honors_overridden_initial_capital() -> None:
    body = {**_BODY, "initial_capital": 250_000.0}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        # Override flows to the engine -> first equity bar starts at 250k. The
        # buy-and-hold reference uses the same starting capital.
        assert result["equity_curve"][0]["equity"] == pytest.approx(250_000.0, rel=1e-3)
        assert result["buy_and_hold_curve"][0]["equity"] == pytest.approx(250_000.0, rel=1e-3)
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_honors_overridden_cost_rate() -> None:
    # CLAUDE.md §8 invariant: costs always reduce returns. A zero-cost run must end at
    # least as high as the default-cost run on the same data + strategy.
    try:
        repo = InMemoryPriceBarRepository()
        adapter = _FakeAdapter()
        client = _client(adapter, repo)
        default_response = client.post("/api/v1/backtest", json=_BODY).json()
        zero_cost_response = client.post(
            "/api/v1/backtest", json={**_BODY, "cost_rate": 0.0}
        ).json()
        assert zero_cost_response["cost_rate"] == 0.0
        assert (
            zero_cost_response["equity_curve"][-1]["equity"]
            >= default_response["equity_curve"][-1]["equity"]
        )
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_rejects_non_positive_initial_capital() -> None:
    # Pydantic gt=0 surfaces as 422 before the handler runs.
    response = TestClient(app).post("/api/v1/backtest", json={**_BODY, "initial_capital": 0})
    assert response.status_code == 422


def test_backtest_endpoint_rejects_negative_cost_rate() -> None:
    response = TestClient(app).post("/api/v1/backtest", json={**_BODY, "cost_rate": -0.001})
    assert response.status_code == 422


def test_backtest_endpoint_supports_triple_ma_alignment() -> None:
    body = {
        **_BODY,
        "strategy": {"name": "triple_ma_alignment", "fast": 5, "medium": 20, "slow": 50},
    }
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["strategy_name"] == "triple_ma_alignment"
        assert result["parameters"] == {"fast": 5, "medium": 20, "slow": 50}
    finally:
        app.dependency_overrides.clear()


_BENCHMARK_KEYS = {
    "benchmark_symbol",
    "alpha",
    "beta",
    "information_ratio",
    "tracking_error",
    "benchmark_relative_drawdown",
}


def test_backtest_endpoint_includes_benchmark_comparison_vs_spy() -> None:
    # ADR-013: every backtest reports alpha/beta/IR/tracking-error/relative-drawdown
    # against SPY, fetched via the same cache-aside path as the requested symbol.
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 200, response.text
        bench = response.json()["benchmark_comparison"]
        assert bench is not None
        assert set(bench) == _BENCHMARK_KEYS
        assert bench["benchmark_symbol"] == "SPY"
        for key in _BENCHMARK_KEYS - {"benchmark_symbol"}:
            assert isinstance(bench[key], float)
        # Relative drawdown is a drawdown => in [-1, 0].
        assert -1.0 <= bench["benchmark_relative_drawdown"] <= 0.0
    finally:
        app.dependency_overrides.clear()


def test_backtest_endpoint_benchmark_present_when_symbol_is_spy() -> None:
    # symbol == SPY reuses the fetched series (no redundant fetch) but still reports a
    # comparison: a strategy on SPY vs. holding SPY is a legitimate question.
    body = {**_BODY, "symbol": "SPY"}
    try:
        response = _client(_FakeAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=body
        )
        assert response.status_code == 200, response.text
        bench = response.json()["benchmark_comparison"]
        assert bench is not None
        assert bench["benchmark_symbol"] == "SPY"
    finally:
        app.dependency_overrides.clear()


class _SparseBenchmarkAdapter(DataSourceAdapter):
    """Returns a healthy series for the requested symbol but too few bars for SPY,
    so the benchmark fetch yields insufficient data."""

    source = "yfinance"
    adapter_version = "fake-sparse-1"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        n = 5 if symbol == "SPY" else 300
        return builders.clean_series(symbol=symbol, n=n)


def test_backtest_endpoint_benchmark_null_when_spy_data_insufficient() -> None:
    # ADR-013: a SPY-fetch shortfall must NOT 500 the core backtest — the field is
    # simply None and the strategy's own result still returns 200.
    try:
        response = _client(_SparseBenchmarkAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["benchmark_comparison"] is None
        # The rest of the backtest is unaffected.
        assert len(body["equity_curve"]) > 0
    finally:
        app.dependency_overrides.clear()


class _RaisingBenchmarkAdapter(DataSourceAdapter):
    """Healthy for the requested symbol; raises when SPY is fetched — simulates a
    data-vendor hiccup that hits only the benchmark leg."""

    source = "yfinance"
    adapter_version = "fake-raise-1"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        if symbol == "SPY":
            raise RuntimeError("benchmark vendor unavailable")
        return builders.clean_series(symbol=symbol, n=300)


def test_backtest_endpoint_benchmark_null_when_spy_fetch_raises() -> None:
    # ADR-013: a raising SPY fetch degrades to no comparison, never a 500.
    try:
        response = _client(_RaisingBenchmarkAdapter(), InMemoryPriceBarRepository()).post(
            "/api/v1/backtest", json=_BODY
        )
        assert response.status_code == 200, response.text
        assert response.json()["benchmark_comparison"] is None
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
