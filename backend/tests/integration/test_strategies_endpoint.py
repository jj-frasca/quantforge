"""GET /api/v1/strategies: returns the catalog of available strategies + their
parameter schemas. Drives the frontend's dynamic strategy form."""

from fastapi.testclient import TestClient

from app.main import app


def test_list_strategies_returns_the_catalog() -> None:
    response = TestClient(app).get("/api/v1/strategies")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 3
    names = [entry["name"] for entry in body]
    # All three currently-built strategies should be in the catalog
    assert "sma" in names
    assert "momentum" in names
    assert "mean_reversion" in names


def test_each_strategy_entry_has_complete_schema() -> None:
    body = TestClient(app).get("/api/v1/strategies").json()
    for entry in body:
        assert set(entry) >= {"name", "label", "description", "citations", "parameters"}
        assert entry["label"], "every strategy needs a human-readable label"
        assert entry["description"], "every strategy needs a description for the UI"
        assert isinstance(entry["parameters"], list)
        for param in entry["parameters"]:
            assert set(param) >= {"name", "type", "default", "label"}
            assert param["type"] in {"int", "float"}
