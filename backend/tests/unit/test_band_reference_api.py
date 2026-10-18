"""ADR-313: serve explicit reference identity without recomputing evidence."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.lab import get_power_calibration_path
from app.main import app
from app.research.lab.calibration import PowerCalibration, collect_power_sweep


@pytest.mark.parametrize("drift", [0.0, -0.0001, 1e-120])
def test_api_retains_band_law_coordinates_and_served_evidence(tmp_path: Path, drift: float) -> None:
    reference = {
        "method": "band_conditional_simple_mean_sign_zero_start_v1",
        "drift": drift,
        "total_vol": 0.012,
        "start_price": 100.0,
    }
    cell = PowerCalibration.model_validate(
        {
            "n_symbols": 1,
            "n_detected": 0,
            "detection_rate": 0.0,
            "n_clear_deflation_bar": 0,
            "deflation_bar": 0.0,
            "edge": "band_reversion",
            "half_life": 3.0,
            "deviation_share": 0.409,
            "band_reference": reference,
            "oracle_sharpes": [1.0],
            "net_oracle_sharpes": [0.9],
            "achievable_oracle_sharpes": [0.4],
            "holdout_years": [2.0],
            "n_bars": [1000],
            "errors": {},
            "gate_config_version": "g",
            "search_config_version": "s",
        }
    )
    sweep = collect_power_sweep([cell])
    path = tmp_path / "power.json"
    original = sweep.model_dump_json()
    path.write_text(original)
    app.dependency_overrides[get_power_calibration_path] = lambda: tmp_path
    try:
        response = TestClient(app).get("/api/v1/power-calibration")
        assert response.status_code == 200
        row = response.json()[0]
        assert row.get("band_reference") == reference
        assert row["cells"][0].get("band_reference") == reference
        assert row["cells"][0]["half_life"] == 3.0
        assert row["cells"][0]["deviation_share"] == 0.409
        assert row["cells"][0]["oracle_sharpes"] == [1.0]
        assert row["cells"][0]["net_oracle_sharpes"] == [0.9]
        assert row["cells"][0]["achievable_oracle_sharpes"] == [0.4]
        assert row["cells"][0]["detection_rate"] == 0.0
        assert row["compatibility"]["status"] == "DIFFERENT"
        assert path.read_text() == original
    finally:
        app.dependency_overrides.pop(get_power_calibration_path, None)
