"""Optional process metadata preserves original scalar provenance (ADR-241)."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import PowerCalibration, collect_power_sweep

FIELDS = ("phi", "half_life", "deviation_share")


def payload() -> dict[str, Any]:
    return {
        "n_symbols": 1,
        "n_detected": 0,
        "detection_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "oracle_sharpes": [0.0],
        "holdout_years": [1.0],
        "n_bars": [252],
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [True, False, "0.5", float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("boundary", ["direct", "json", "sweep"])
def test_invalid_original_process_metadata_is_refused(
    field: str, value: Any, boundary: str
) -> None:
    with pytest.raises(ValidationError, match=r"finite.*numbers"):
        if boundary == "direct":
            PowerCalibration.model_validate(payload() | {field: value})
        elif boundary == "json":
            PowerCalibration.model_validate_json(json.dumps(payload() | {field: value}))
        else:
            corrupt = PowerCalibration.model_validate(payload()).model_copy(update={field: value})
            collect_power_sweep([corrupt])


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [np.bool_(True), 10**400, Fraction(10**400, 1), 1j])
def test_unrepresentable_or_nonreal_metadata_is_refused(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {field: value})


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [None, -2, 0, 2, Fraction(1, 2), np.float32(0.25), np.int64(3)])
def test_optional_and_broad_finite_metadata_remains_valid(field: str, value: Any) -> None:
    cell = PowerCalibration.model_validate(payload() | {field: value})
    expected = None if value is None else float(value)
    assert getattr(cell, field) == expected
    assert PowerCalibration.model_validate_json(cell.model_dump_json()) == cell
    assert collect_power_sweep([cell]).cells == [cell]


def test_absent_process_metadata_keeps_legacy_defaults() -> None:
    cell = PowerCalibration.model_validate(payload())
    assert all(getattr(cell, field) is None for field in FIELDS)
    assert cell.edge == "ar1"
    assert PowerCalibration.model_validate_json(cell.model_dump_json()) == cell


@given(st.sampled_from(FIELDS), st.booleans())
def test_boolean_metadata_never_becomes_process_number(field: str, value: bool) -> None:
    with pytest.raises(ValidationError, match=r"finite.*numbers"):
        PowerCalibration.model_validate(payload() | {field: value})


@given(st.sampled_from(FIELDS), st.floats(allow_nan=False, allow_infinity=False))
def test_finite_process_metadata_round_trips(field: str, value: float) -> None:
    cell = PowerCalibration.model_validate(payload() | {field: value})
    assert getattr(cell, field) == value
    assert PowerCalibration.model_validate_json(cell.model_dump_json()) == cell
