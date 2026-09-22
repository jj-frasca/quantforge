"""ADR-102's pre-registered probability-DSR gate comparison, before any data are read."""

import pytest

from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    NullCalibration,
    NullSymbolDiagnostics,
    PowerCalibration,
    PowerSweep,
)
from app.research.lab.gate import GateResult
from app.research.lab.probability_dsr import compare_probability_dsr_gate

GATE_VERSION = "gate-v1"
SEARCH_VERSION = "search-v1"
N_BARS = 7_400


def _verdict(symbol: str, *, incumbent: bool, candidate: bool) -> CalibrationSymbolVerdict:
    gate = GateResult(
        passed=incumbent,
        dsr_ok=incumbent,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        beats_buy_and_hold_ok=True,
        required_track_record_years=1.0,
        gate_config_version=GATE_VERSION,
        holdout_sharpe=5.0,
        holdout_n_bars=252,
    )
    return CalibrationSymbolVerdict(
        symbol=symbol,
        deflated_sharpe_probability=0.99 if candidate else 0.10,
        gate_result=gate,
        holdout_sharpe=5.0,
        holdout_n_bars=252,
    )


def _null(mode: str, *, n: int = 200) -> NullCalibration:
    verdicts = [_verdict(f"{mode}-{i}", incumbent=False, candidate=False) for i in range(n)]
    diagnostics = [
        NullSymbolDiagnostics(
            symbol=verdict.symbol,
            n_bars=N_BARS,
            holdout_years=1.0,
            deflated_sharpe_probability=verdict.deflated_sharpe_probability,
            calibration_verdict=verdict,
        )
        for verdict in verdicts
    ]
    return NullCalibration(
        n_symbols=n,
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=3.0,
        max_deflated_sharpe=-0.1,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[1.0] * n,
        n_bars=[N_BARS] * n,
        symbol_diagnostics=diagnostics,
        errors={},
        gate_config_version=GATE_VERSION,
        search_config_version=SEARCH_VERSION,
        refine=True,
        null_mode=mode,
    )


def _cell(phi: float, *, incumbent_n: int = 10, candidate_n: int = 20) -> PowerCalibration:
    verdicts = [
        _verdict(
            f"EDGE-{phi:+.1f}-{i}",
            incumbent=i < incumbent_n,
            candidate=i < candidate_n,
        )
        for i in range(50)
    ]
    return PowerCalibration(
        n_symbols=50,
        n_detected=incumbent_n,
        detection_rate=incumbent_n / 50,
        n_clear_deflation_bar=incumbent_n,
        deflation_bar=3.0,
        phi=phi,
        oracle_sharpes=[4.0] * 50,
        finalist_deflated_sharpe_probabilities=[
            verdict.deflated_sharpe_probability for verdict in verdicts
        ],
        symbol_verdicts=verdicts,
        holdout_years=[1.0] * 50,
        n_bars=[N_BARS] * 50,
        errors={},
        gate_config_version=GATE_VERSION,
        search_config_version=SEARCH_VERSION,
        refine=True,
    )


def _sweep(*, incumbent_n: int = 10, candidate_n: int = 20) -> PowerSweep:
    return PowerSweep(
        edge="ar1",
        gate_config_version=GATE_VERSION,
        search_config_version=SEARCH_VERSION,
        n_bars=N_BARS,
        cells=[
            _cell(-0.30, incumbent_n=incumbent_n, candidate_n=candidate_n),
            _cell(+0.30, incumbent_n=incumbent_n, candidate_n=candidate_n),
        ],
    )


def test_preregistered_probability_gate_accepts_only_the_fixed_joint_improvement() -> None:
    result = compare_probability_dsr_gate(
        [_null("iid_normal"), _null("bootstrap:SPY")],
        _sweep(),
    )

    assert result.threshold == pytest.approx(0.95)
    assert result.passed is True
    assert result.null_candidate_graduates == {"bootstrap:SPY": 0, "iid_normal": 0}
    assert [cell.candidate_detections for cell in result.strong_edge_cells] == [20, 20]
    assert result.candidate_only == 20
    assert result.incumbent_only == 0
    assert result.mcnemar_pvalue < 0.05


def test_probability_gate_refuses_no_improvement_even_when_type_i_is_zero() -> None:
    result = compare_probability_dsr_gate(
        [_null("iid_normal"), _null("bootstrap:SPY")],
        _sweep(incumbent_n=10, candidate_n=10),
    )

    assert result.passed is False
    assert result.candidate_only == result.incumbent_only == 0
    assert result.mcnemar_pvalue == pytest.approx(1.0)


def test_probability_gate_refuses_a_directional_regression_despite_pooled_improvement() -> None:
    sweep = PowerSweep(
        edge="ar1",
        gate_config_version=GATE_VERSION,
        search_config_version=SEARCH_VERSION,
        n_bars=N_BARS,
        cells=[
            _cell(-0.30, incumbent_n=20, candidate_n=10),
            _cell(+0.30, incumbent_n=0, candidate_n=30),
        ],
    )

    result = compare_probability_dsr_gate([_null("iid_normal"), _null("bootstrap:SPY")], sweep)

    assert result.candidate_only == 30
    assert result.incumbent_only == 10
    assert result.mcnemar_pvalue < 0.05
    assert result.passed is False


def test_probability_gate_refuses_incomplete_legacy_joint_verdicts() -> None:
    legacy = _null("iid_normal")
    payload = legacy.model_dump()
    for diagnostic in payload["symbol_diagnostics"]:
        diagnostic.pop("calibration_verdict")
    legacy = NullCalibration.model_validate(payload)

    with pytest.raises(ValueError, match="joint verdict"):
        compare_probability_dsr_gate([legacy, _null("bootstrap:SPY")], _sweep())


def test_probability_gate_refuses_mismatched_measurement_identity() -> None:
    bootstrap = _null("bootstrap:SPY").model_copy(update={"search_config_version": "other"})

    with pytest.raises(ValueError, match="search_config_version"):
        compare_probability_dsr_gate([_null("iid_normal"), bootstrap], _sweep())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("edge", "band_reversion", "edge"),
        ("gate_config_version", "other-gate", "gate_config_version"),
        ("search_config_version", "other-search", "search_config_version"),
        ("n_bars", [N_BARS - 1] * 50, "n_bars"),
    ],
)
def test_probability_gate_binds_power_cells_to_their_sweep(
    field: str, value: object, message: str
) -> None:
    sweep = _sweep()
    cells = [sweep.cells[0].model_copy(update={field: value}), sweep.cells[1]]
    mismatched = sweep.model_copy(update={"cells": cells})

    with pytest.raises(ValueError, match=message):
        compare_probability_dsr_gate([_null("iid_normal"), _null("bootstrap:SPY")], mismatched)


def test_probability_gate_binds_embedded_verdict_to_its_calibration_gate() -> None:
    iid = _null("iid_normal")
    payload = iid.model_dump()
    payload["symbol_diagnostics"][0]["calibration_verdict"]["gate_result"][
        "gate_config_version"
    ] = "other-gate"
    mismatched = NullCalibration.model_validate(payload)

    with pytest.raises(ValueError, match="embedded gate_config_version"):
        compare_probability_dsr_gate([mismatched, _null("bootstrap:SPY")], _sweep())


def test_probability_gate_refuses_duplicate_strong_edge_cells() -> None:
    sweep = _sweep()
    duplicate = sweep.model_copy(update={"cells": [*sweep.cells, _cell(-0.30)]})

    with pytest.raises(ValueError, match="duplicate"):
        compare_probability_dsr_gate([_null("iid_normal"), _null("bootstrap:SPY")], duplicate)
