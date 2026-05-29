"""CORS middleware: allowed dev origins are echoed; disallowed origins are not."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_allows_the_dev_origin() -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_does_not_echo_a_disallowed_origin() -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
