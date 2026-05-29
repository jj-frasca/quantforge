"""Health endpoint: returns 200 with status 'ok' and the configured environment."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200_ok_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint_reports_environment() -> None:
    response = client.get("/health")
    body = response.json()
    assert "environment" in body
    assert isinstance(body["environment"], str)
