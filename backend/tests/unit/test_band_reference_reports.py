"""ADR-313 reports declare nominal laws without restating numeric evidence."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from scripts import compare_power_sweeps as compare
from scripts import consolidate_power_calibration as consolidate
from scripts import horizon_power_calibration as horizon

from app.research.lab.calibration import BandReference, PowerCalibration, PowerSweep

METHOD = "band_conditional_simple_mean_sign_zero_start_v1"


def cell(*, known: bool) -> PowerCalibration:
    result = PowerCalibration(
        n_symbols=2,
        n_detected=1,
        detection_rate=0.5,
        n_clear_deflation_bar=0,
        deflation_bar=2.75,
        edge="band_reversion",
        half_life=3.0,
        deviation_share=0.409,
        oracle_sharpes=[4.0, 6.0],
        net_oracle_sharpes=[3.0, 5.0],
        achievable_oracle_sharpes=[2.0, 4.0],
        finalist_observed_sharpes=[1.0, 3.0],
        holdout_years=[1.0, 1.0],
        n_bars=[1000, 1000],
        errors={},
        gate_config_version="gate-fixture",
        band_reference=(
            BandReference(method=METHOD, drift=0.0003, total_vol=0.012, start_price=100.0)
            if known
            else None
        ),
    )
    return result


@pytest.mark.parametrize("known", [True, False])
def test_horizon_reports_known_or_unknown_identity(
    known: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    horizon._report(cell(known=known))
    output = capsys.readouterr().out
    if known:
        for part in (
            METHOD,
            "0.0003",
            "0.012",
            "100.0",
            "full-price",
            "nominal",
            "simple-mean",
            "+3.00",
            "66.7%",
        ):
            assert part in output
        assert "startup/posterior not certified" not in output
    else:
        assert "unknown" in output
        assert "historical driver uses log-mean signs" in output


@pytest.mark.parametrize("known", [True, False])
def test_consolidated_report_declares_band_identity_and_cell_share(
    known: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    one = cell(known=known)
    sweep = PowerSweep.model_construct(
        edge="band_reversion",
        n_bars=1000,
        cells=[one],
        gate_config_version="gate-fixture",
        search_config_version="search-fixture",
        band_reference=one.band_reference,
    )
    consolidate._report(sweep)
    output = capsys.readouterr().out
    assert (METHOD if known else "unknown") in output
    assert "deviation share 0.409" in output
    assert "+5.00" in output


@pytest.mark.parametrize("known", [True, False])
def test_comparison_reports_band_identity_and_shares(
    known: bool, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    one = cell(known=known)
    sweep = PowerSweep.model_construct(
        edge="band_reversion",
        n_bars=1000,
        cells=[one],
        gate_config_version="gate-fixture",
        search_config_version="search-fixture",
        band_reference=one.band_reference,
    )
    monkeypatch.setattr("sys.argv", ["compare", "before", "after"])
    monkeypatch.setattr(Path, "read_text", Mock(return_value="{}"))
    monkeypatch.setattr(PowerSweep, "model_validate_json", Mock(return_value=sweep))
    monkeypatch.setattr(compare, "compare_power_sweeps", Mock(return_value=[]))
    compare.main()
    output = capsys.readouterr().out
    assert (METHOD if known else "unknown") in output
    assert "deviation share 0.409" in output
