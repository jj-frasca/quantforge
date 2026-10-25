"""F310: a relative-rank diagnostic cannot establish a profitable edge."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import validation as api
from app.dependencies import get_data_adapter, get_repository
from app.research.backtesting.metrics import sharpe_ratio
from app.validation.engine import ValidationEngine, _interpret


@pytest.mark.parametrize(
    ("pbo", "level", "verdict"),
    [
        (0.0, "low", "good"),
        (0.2999, "low", "good"),
        (0.3, "moderate", "warning"),
        (0.4999, "moderate", "warning"),
        (0.5, "high", "bad"),
        (1.0, "high", "bad"),
    ],
)
def test_pbo_interpretation_bounds_inference_at_existing_display_cutoffs(
    pbo: float, level: str, verdict: str
) -> None:
    interpretation = _interpret(pbo, 0.5, 0.8)[0]
    assert interpretation.metric == "pbo"
    assert interpretation.verdict == verdict
    assert interpretation.message.startswith(f"PBO {pbo:.0%}")
    assert level in interpretation.message
    assert "at or below the out-of-sample midpoint" in interpretation.message
    assert "among tested configurations" in interpretation.message
    assert "does not establish a profitable edge or future performance" in interpretation.message
    assert "unlikely to be a backtest artifact" not in interpretation.message
    assert "probability the strategy is overfit" not in interpretation.message


def test_validate_losing_candidates_with_zero_pbo_retains_rejection_and_qualifies_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    n = 300
    frame = pd.DataFrame(
        {"close": 100 + np.arange(n) * 0.1},
        index=pd.date_range("2020-01-01", periods=n, tz="UTC"),
    )
    candidates = [SimpleNamespace(parameters={"lookback": i + 2}, column=i) for i in range(2)]
    returns = np.column_stack([np.tile([-0.001, -0.003], n // 2), np.tile([-0.01, -0.012], n // 2)])
    assert np.all(returns < 0)

    class FakeEngine:
        def run_strategy(self, data: pd.DataFrame, strategy: SimpleNamespace) -> SimpleNamespace:
            series = pd.Series(returns[:, strategy.column], index=data.index)
            return SimpleNamespace(
                returns=series, metrics=SimpleNamespace(sharpe=sharpe_ratio(series))
            )

    engine = ValidationEngine(backtest_engine=FakeEngine())
    application = FastAPI()
    application.include_router(api.router, prefix="/api/v1")
    application.dependency_overrides[get_data_adapter] = lambda: None
    application.dependency_overrides[get_repository] = lambda: None
    monkeypatch.setattr(api, "_load_frame", lambda *args: frame)
    monkeypatch.setattr(api, "grid_from_catalog", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(api, "ValidationEngine", lambda: engine)
    monkeypatch.setattr(ValidationEngine, "_regime_breakdown", lambda *args: {})

    response = TestClient(application).post(
        "/api/v1/validate",
        json={
            "symbol": "SYNTH",
            "strategy": "sma",
            "start_date": "2020-01-01T00:00:00Z",
            "end_date": "2022-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pbo"] == 0.0
    assert body["observed_sharpe"] == pytest.approx(-31.69605653705205, rel=1e-12)
    assert body["deflated_sharpe"] == pytest.approx(-84.11662332576813, rel=1e-12)
    assert body["passed"] is False
    interpretation = next(item for item in body["interpretations"] if item["metric"] == "pbo")
    assert interpretation["verdict"] == "good"
    assert "does not establish a profitable edge or future performance" in interpretation["message"]
