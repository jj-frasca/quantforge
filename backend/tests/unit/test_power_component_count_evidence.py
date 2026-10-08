"""Component attribution requires original counts against searched symbols."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import PowerCalibration, collect_power_sweep

COMPONENTS = ["dsr", "pbo", "stability", "mintrl", "holdout", "beats_buy_and_hold"]


def payload(counts: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_symbols": 2,
        "n_detected": 0,
        "detection_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "phi": 0.3,
        "oracle_sharpes": [],
        "holdout_years": [1.0, 1.0],
        "n_bars": [1260, 1260],
        "errors": {},
        "gate_config_version": "gate",
        "gate_pass_counts": counts,
    }


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("value", [True, False, "1", 1.0, Fraction(1, 1), -1, 3])
def test_component_counts_reject_invalid_original_evidence(component: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload({component: value}))


@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 3])
def test_component_json_rejects_coercion_and_impossible_counts(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate_json(json.dumps(payload({"dsr": value})))


@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 3])
def test_sweep_rejects_unchecked_component_mapping(value: Any) -> None:
    root = PowerCalibration.model_validate(payload({"dsr": 1}))
    unchecked = root.model_copy(update={"gate_pass_counts": {"dsr": value}})
    with pytest.raises(ValidationError):
        collect_power_sweep([unchecked])


@pytest.mark.parametrize(
    "counts", [{}, {"dsr": 0}, {"dsr": 2}, {"dsr": np.int64(1)}, {"legacy-name": 0}]
)
def test_legacy_mapping_and_integer_boundaries_remain(counts: dict[str, Any]) -> None:
    root = PowerCalibration.model_validate(payload(counts))
    assert root.gate_pass_counts == counts
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root
    assert collect_power_sweep([root]).cells[0] == root


def test_all_six_component_counts_round_trip_without_changing_attribution() -> None:
    counts = dict(zip(COMPONENTS, [0, 1, 2, 0, 1, 2], strict=True))
    root = PowerCalibration.model_validate(payload(counts))
    assert PowerCalibration.model_validate_json(root.model_dump_json()).gate_pass_counts == counts


@pytest.mark.parametrize("value", [True, 3])
def test_unknown_mapping_keys_still_require_valid_count_evidence(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload({"legacy-name": value}))
