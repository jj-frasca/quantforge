"""A modern diagnostic's years describe its canonical locked holdout (ADR-225)."""

import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    NullCalibration,
    NullSymbolDiagnostics,
    merge_calibrations,
)
from app.research.lab.gate import GateResult


def diagnostic_payload(*, bars: int = 252, years: float = 1.0) -> dict[str, Any]:
    verdict = CalibrationSymbolVerdict(
        symbol="A",
        deflated_sharpe_probability=None,
        holdout_sharpe=2.0,
        holdout_n_bars=bars,
        gate_result=GateResult(
            passed=False,
            dsr_ok=False,
            pbo_ok=True,
            stability_ok=True,
            mintrl_ok=True,
            holdout_ok=True,
            beats_buy_and_hold_ok=True,
            required_track_record_years=1.0,
            gate_config_version="gate",
            holdout_sharpe=2.0,
            holdout_n_bars=bars,
        ),
    )
    return {
        "symbol": "A",
        "n_bars": 7400,
        "holdout_years": years,
        "calibration_verdict": verdict.model_dump(mode="json"),
    }


def root_payload(diagnostic: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_symbols": 1,
        "n_graduates": 0,
        "false_graduation_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "max_deflated_sharpe": -1.0,
        "max_holdout_sharpe": None,
        "graduates": [],
        "holdout_years": [diagnostic["holdout_years"]],
        "n_bars": [7400],
        "symbol_diagnostics": [diagnostic],
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("years", [0.5, 2.0, 100.0])
@pytest.mark.parametrize("channel", ["leaf", "json", "root"])
def test_modern_history_attribution_rejects_contradictory_years(years: float, channel: str) -> None:
    data = diagnostic_payload(years=years)
    with pytest.raises(ValidationError, match="holdout_years"):
        if channel == "leaf":
            NullSymbolDiagnostics.model_validate(data)
        elif channel == "json":
            NullSymbolDiagnostics.model_validate_json(json.dumps(data))
        else:
            NullCalibration.model_validate(root_payload(data))


@pytest.mark.parametrize("channel", ["leaf", "root", "merge"])
def test_unchecked_history_attribution_is_revalidated(channel: str) -> None:
    original = NullSymbolDiagnostics.model_validate(diagnostic_payload())
    bad = original.model_copy(update={"holdout_years": 2.0})
    root = NullCalibration.model_validate(root_payload(original.model_dump(mode="json")))
    copied = root.model_copy(update={"symbol_diagnostics": [bad], "holdout_years": [2.0]})
    with pytest.raises(ValidationError, match="holdout_years"):
        if channel == "leaf":
            NullSymbolDiagnostics.model_validate(bad)
        elif channel == "root":
            NullCalibration.model_validate(copied.model_dump(round_trip=True))
        else:
            merge_calibrations([copied])


@pytest.mark.parametrize("years", [0.5, 2.0, 100.0])
def test_absent_legacy_verdict_keeps_positive_history(years: float) -> None:
    data = diagnostic_payload(years=years) | {"calibration_verdict": None}
    leaf = NullSymbolDiagnostics.model_validate(data)
    root = NullCalibration.model_validate(root_payload(data))
    assert leaf.holdout_years == root.holdout_years[0] == years
    assert merge_calibrations([root]) == root


@pytest.mark.parametrize("bars", [2, 252, 1480, 5000])
def test_exact_history_ratio_and_nullable_probability_round_trip(bars: int) -> None:
    data = diagnostic_payload(bars=bars, years=bars / 252)
    leaf = NullSymbolDiagnostics.model_validate(data)
    assert leaf.calibration_verdict is not None
    assert leaf.calibration_verdict.deflated_sharpe_probability is None
    assert NullSymbolDiagnostics.model_validate_json(leaf.model_dump_json()) == leaf
    root = NullCalibration.model_validate(root_payload(data))
    assert merge_calibrations([root]) == root


@given(st.integers(min_value=1, max_value=1_000_000))
def test_canonical_holdout_bars_define_exact_year_projection(bars: int) -> None:
    data = diagnostic_payload(bars=bars, years=bars / 252)
    leaf = NullSymbolDiagnostics.model_validate(data)
    assert leaf.holdout_years == bars / 252
    assert NullSymbolDiagnostics.model_validate_json(leaf.model_dump_json()) == leaf
