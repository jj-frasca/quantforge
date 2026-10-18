"""F159: console comparisons retain evidence without claiming reference bounds."""

from typing import Any

import pytest
from scripts.horizon_power_calibration import _report

from app.research.lab.calibration import PowerCalibration


def report_cell(**updates: Any) -> PowerCalibration:
    return PowerCalibration.model_validate(
        {
            "n_symbols": 2,
            "n_detected": 1,
            "detection_rate": 0.5,
            "n_clear_deflation_bar": 0,
            "deflation_bar": 2.75,
            "edge": "band_reversion",
            "half_life": 3.0,
            "deviation_share": 0.409,
            "oracle_sharpes": [4.0, 6.0],
            "net_oracle_sharpes": [3.0, 5.0],
            "achievable_oracle_sharpes": [2.0, 4.0],
            "finalist_observed_sharpes": [1.0, 3.0],
            "holdout_years": [1.0, 1.0],
            "n_bars": [1000, 1000],
            "gate_pass_counts": {"dsr": 1},
            "errors": {"UNSEARCHABLE": "fixture error"},
            "gate_config_version": "gate-fixture",
            "search_config_version": "search-fixture",
        }
        | updates
    )


def test_report_qualifies_references_and_preserves_measured_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = report_cell()
    before = result.model_dump_json()
    _report(result)
    text = capsys.readouterr().out
    assert "CAPTURE UPPER BOUND" not in text
    assert "recoverable edge" not in text
    assert "effect size actually planted" not in text
    assert "historical driver uses log-mean signs scored on simple returns" in text
    assert "supplied method/source law not recorded" in text
    assert "filter startup/posterior not certified" in text
    assert "no cost-aware optimum, sample maximum or no-edge conclusion" in text
    assert "selection-biased" in text
    for line in (
        "planted process     : band_reversion",
        "reversion half-life : 3.0 bars (deviation share 0.409)",
        "gate config version : gate-fixture",
        "search config version: search-fixture",
        "adaptive refinement : False (span 0.25)",
        "symbols searched    : 2",
        "bars per symbol     : 1000 (supplied synthetic history)",
        "detected            : 1",
        "DETECTION RATE      : 50.0%  <- power of the gate as such",
        "gate component pass : dsr 1/2",
        "clear ADR-018 bar   : 0 (bar 2.75)",
        "latent reference gross: median +5.00 | p95 +5.90 | max +6.00",
        "latent reference net: median +4.00 | p95 +4.90 | max +5.00",
        "ADR-055: the same 10bp the catalog pays on turnover",
        "capture vs gross reference: 40.0%",
        "  net of costs      : 50.0%",
        "filtered reference net: +3.00",
        "  capture vs filtered reference: 66.7%",
        "unsearchable        : 1 symbol(s)",
    ):
        assert line in text
    assert result.model_dump_json() == before


@pytest.mark.parametrize(
    "updates",
    [
        {"achievable_oracle_sharpes": [0.001, 0.001]},
        {"achievable_oracle_sharpes": [0.0, 0.0]},
        {"n_bars": []},
        {"finalist_observed_sharpes": [1.0]},
    ],
    ids=["small-denominator", "zero-denominator", "missing-history", "partial-finalists"],
)
def test_refused_filtered_ratio_does_not_infer_no_edge_or_a_noise_only_cause(
    updates: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    result = report_cell(**updates)
    assert result.achievable_capture_ratio is None
    _report(result)
    text = capsys.readouterr().out
    assert "capture vs filtered reference: REFUSED" in text
    assert "existing evidence/denominator requirements" in text
    assert "does not establish absence of tradeable edge" in text
    assert "inside its own Sharpe standard error" not in text
    assert "nothing to express a fraction of" not in text
    assert "recoverable edge" not in text


def test_absent_optional_evidence_does_not_print_invented_scores_or_ratios(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = report_cell(
        oracle_sharpes=[],
        net_oracle_sharpes=[],
        achievable_oracle_sharpes=[],
        finalist_observed_sharpes=[],
        n_bars=[],
    )
    _report(result)
    text = capsys.readouterr().out
    for absent in (
        "latent reference gross:",
        "latent reference net:",
        "filtered reference net:",
        "capture vs",
        "bars per symbol",
    ):
        assert absent not in text
    assert "supplied method/source law not recorded" in text
    assert "symbols searched    : 2" in text
