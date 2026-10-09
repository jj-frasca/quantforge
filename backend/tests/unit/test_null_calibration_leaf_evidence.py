"""ADR-213: intrinsic scalar evidence, including standalone and copied leaves."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import (
    NullCalibration,
    NullGraduate,
    NullSymbolDiagnostics,
    merge_calibrations,
)


def graduate_payload() -> dict[str, Any]:
    return {
        "symbol": "NULL0000",
        "holdout_sharpe": 2.0,
        "holdout_n_bars": 1260,
        "deflated_sharpe": 0.1,
    }


def diagnostic_payload() -> dict[str, Any]:
    return {"symbol": "NULL0000", "n_bars": 6300, "holdout_years": 5.0}


@pytest.mark.parametrize("field", ["holdout_sharpe", "deflated_sharpe"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "1.2", 1j])
def test_graduate_rejects_invalid_original_scores(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        NullGraduate.model_validate(graduate_payload() | {field: value})


@pytest.mark.parametrize(
    "field",
    [
        "walk_forward_oos_sharpe",
        "walk_forward_hold_sharpe",
        "purged_cv_oos_sharpe",
        "purged_cv_hold_sharpe",
        "deflated_sharpe_probability",
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0.5", 1j])
def test_diagnostic_rejects_invalid_original_scores(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        NullSymbolDiagnostics.model_validate(diagnostic_payload() | {field: value})


@pytest.mark.parametrize("value", [0, -1, True, 1.0, "1260"])
@pytest.mark.parametrize("leaf", ["graduate", "diagnostic"])
def test_leaf_requires_positive_original_integer_history(leaf: str, value: object) -> None:
    with pytest.raises(ValidationError):
        if leaf == "graduate":
            NullGraduate.model_validate(graduate_payload() | {"holdout_n_bars": value})
        else:
            NullSymbolDiagnostics.model_validate(diagnostic_payload() | {"n_bars": value})


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "5.0"])
def test_diagnostic_requires_positive_finite_original_holdout_years(value: object) -> None:
    with pytest.raises(ValidationError):
        NullSymbolDiagnostics.model_validate(diagnostic_payload() | {"holdout_years": value})


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_diagnostic_probability_has_probability_range(value: float) -> None:
    with pytest.raises(ValidationError):
        NullSymbolDiagnostics.model_validate(
            diagnostic_payload() | {"deflated_sharpe_probability": value}
        )


@pytest.mark.parametrize("value", [Fraction(2**54 + 1, 2**54), Fraction(-1, 10**400)])
def test_diagnostic_rejects_original_probability_outside_range_before_float_rounding(
    value: Fraction,
) -> None:
    with pytest.raises(ValidationError):
        NullSymbolDiagnostics.model_validate(
            diagnostic_payload() | {"deflated_sharpe_probability": value}
        )


@pytest.mark.parametrize("value", [-2.0, 0.0, np.float64(1.2), Fraction(-1, 3)])
def test_finite_signed_scores_and_numpy_integer_history_remain_valid(
    value: float | Fraction,
) -> None:
    graduate = NullGraduate.model_validate(
        graduate_payload() | {"holdout_sharpe": value, "holdout_n_bars": np.int64(1260)}
    )
    diagnostic = NullSymbolDiagnostics.model_validate(
        diagnostic_payload() | {"walk_forward_oos_sharpe": value, "n_bars": np.int64(6300)}
    )
    assert graduate.holdout_sharpe == diagnostic.walk_forward_oos_sharpe == float(value)


@pytest.mark.parametrize("value", [None, 0.0, 1.0])
def test_unmeasured_and_boundary_probability_remain_valid(value: float | None) -> None:
    row = NullSymbolDiagnostics.model_validate(
        diagnostic_payload() | {"deflated_sharpe_probability": value}
    )
    assert row.deflated_sharpe_probability == value
    assert row.calibration_verdict is None
    assert row.walk_forward_oos_sharpe is None


@pytest.mark.parametrize("leaf", ["graduate", "diagnostic"])
def test_json_loading_rejects_nonfinite_score_evidence(leaf: str) -> None:
    with pytest.raises(ValidationError):
        if leaf == "graduate":
            NullGraduate.model_validate_json(
                json.dumps(graduate_payload() | {"holdout_sharpe": float("nan")})
            )
        else:
            NullSymbolDiagnostics.model_validate_json(
                json.dumps(diagnostic_payload() | {"walk_forward_oos_sharpe": float("inf")})
            )


def calibration_payload() -> dict[str, Any]:
    return {
        "n_symbols": 1,
        "n_graduates": 1,
        "false_graduation_rate": 1.0,
        "n_clear_deflation_bar": 1,
        "deflation_bar": 0.0,
        "max_deflated_sharpe": 0.1,
        "max_holdout_sharpe": 2.0,
        "graduates": [graduate_payload()],
        "holdout_years": [5.0],
        "n_bars": [6300],
        "errors": {},
        "gate_config_version": "gate",
        "search_config_version": "search",
        "null_mode": "iid_normal",
    }


def test_root_attachment_revalidates_unchecked_graduate_score() -> None:
    row = NullGraduate.model_validate(graduate_payload()).model_copy(
        update={"holdout_sharpe": float("nan")}
    )
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(calibration_payload() | {"graduates": [row]})


def test_root_attachment_revalidates_unchecked_diagnostic_score() -> None:
    row = NullSymbolDiagnostics.model_validate(diagnostic_payload()).model_copy(
        update={"walk_forward_oos_sharpe": float("inf")}
    )
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(
            calibration_payload()
            | {"symbol_diagnostics": [row], "walk_forward_oos_sharpes": [float("inf")]}
        )


def test_merge_rejects_unchecked_nonfinite_graduate_instead_of_suppressing_survival() -> None:
    root = NullCalibration.model_validate(calibration_payload())
    row = root.graduates[0].model_copy(update={"holdout_sharpe": float("nan")})
    corrupted = root.model_copy(update={"graduates": [row]})
    with pytest.raises(ValidationError):
        merge_calibrations([corrupted])
