from pathlib import Path

import pytest
from scripts.consolidate_null_calibration import _artifact_path, _migrate_legacy_artifacts

from app.research.lab.calibration import NullCalibration


def _calibration(mode: str, n_bars: list[int]) -> NullCalibration:
    return NullCalibration(
        n_symbols=len(n_bars),
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.0,
        max_deflated_sharpe=-0.1,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[4.0] * len(n_bars),
        n_bars=n_bars,
        errors={},
        gate_config_version="gate",
        search_config_version="search",
        null_mode=mode,
    )


def test_artifact_path_names_null_mode_and_measured_history(tmp_path: Path) -> None:
    result = _calibration("bootstrap:SPY", [7400, 7400])

    assert _artifact_path(tmp_path, result) == tmp_path / "bootstrap_spy_7400.json"


def test_artifact_path_refuses_an_unversioned_history(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="n_bars"):
        _artifact_path(tmp_path, _calibration("iid_normal", []))


def test_legacy_artifacts_migrate_to_their_recorded_identity(tmp_path: Path) -> None:
    iid = _calibration("iid_normal", [7400])
    bootstrap = _calibration("bootstrap:SPY", [7400])
    (tmp_path / "iid_normal.json").write_text(iid.model_dump_json())
    (tmp_path / "bootstrap.json").write_text(bootstrap.model_dump_json())

    _migrate_legacy_artifacts(tmp_path)

    assert (tmp_path / "iid_normal_7400.json").exists()
    assert (tmp_path / "bootstrap_spy_7400.json").exists()
    assert not (tmp_path / "iid_normal.json").exists()
    assert not (tmp_path / "bootstrap.json").exists()
