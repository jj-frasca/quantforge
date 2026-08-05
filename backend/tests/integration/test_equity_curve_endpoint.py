"""Read-only equity-curve endpoint: the headline "are we making money?" view. Returns the committed
paper-account equity snapshots oldest-first. Mirrors the graduates endpoint — reads the committed
JSON series with a dependency-injected path so tests feed a synthetic file (no network/DB/broker)."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.equity_curve import get_equity_curve_path
from app.execution.equity_curve import EquityPoint, JsonFileEquityCurve
from app.main import app


def _point(ts: str, equity: float) -> EquityPoint:
    return EquityPoint(
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=UTC),
        equity=equity,
        cash=equity / 2,
        n_positions=3,
        return_since_start=equity / 100_000.0 - 1.0,
    )


def test_default_equity_curve_path_points_at_the_in_repo_data_dir() -> None:
    assert get_equity_curve_path().name == "equity_curve.json"
    assert get_equity_curve_path().parent.name == "data"


def test_equity_curve_returns_points_oldest_first(tmp_path) -> None:
    path = tmp_path / "equity_curve.json"
    JsonFileEquityCurve(path).save(
        [_point("2026-08-01T00:00:00", 100_000.0), _point("2026-08-05T00:00:00", 92_488.99)]
    )
    app.dependency_overrides[get_equity_curve_path] = lambda: path
    try:
        body = TestClient(app).get("/api/v1/equity-curve").json()
        assert [p["equity"] for p in body] == [100_000.0, 92_488.99]  # oldest-first, preserved
        assert body[0]["cash"] == 50_000.0
        assert body[0]["n_positions"] == 3
        assert body[1]["return_since_start"] == 92_488.99 / 100_000.0 - 1.0
    finally:
        app.dependency_overrides.clear()


def test_equity_curve_is_empty_when_file_absent(tmp_path) -> None:
    app.dependency_overrides[get_equity_curve_path] = lambda: tmp_path / "nope.json"
    try:
        assert TestClient(app).get("/api/v1/equity-curve").json() == []
    finally:
        app.dependency_overrides.clear()
