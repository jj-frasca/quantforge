"""Power counts and their rate describe the same measured experiment."""

from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import PowerCalibration, collect_power_sweep


def payload() -> dict[str, Any]:
    return {
        "n_symbols": 2,
        "n_detected": 1,
        "detection_rate": 0.5,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 1.5,
        "phi": 0.3,
        "oracle_sharpes": [],
        "holdout_years": [5.0, 5.0],
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("field", ["n_symbols", "n_detected", "n_clear_deflation_bar"])
@pytest.mark.parametrize("value", [True, False, -1, 1.0, "1"])
def test_power_counts_require_original_nonboolean_integers(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {field: value})


@pytest.mark.parametrize("field", ["detection_rate", "deflation_bar"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0.5", -0.1])
def test_power_root_scores_require_original_finite_bounded_reals(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {field: value})


@pytest.mark.parametrize(
    "update",
    [
        {"n_symbols": 0},
        {"n_detected": 3, "detection_rate": 1.5},
        {"n_clear_deflation_bar": 2},
        {"detection_rate": 0.4},
        {"detection_rate": 1.1},
        {"n_detected": 0, "detection_rate": 0.0, "n_clear_deflation_bar": 1},
        {"detection_rate": Fraction(10**400 + 1, 10**400), "n_detected": 2},
        {"deflation_bar": Fraction(-1, 10**400)},
    ],
)
def test_power_root_rejects_incoherent_original_claims(update: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | update)


@pytest.mark.parametrize(
    "field,value",
    [
        ("n_symbols", 0),
        ("n_detected", 3),
        ("n_clear_deflation_bar", 2),
        ("detection_rate", float("nan")),
        ("deflation_bar", float("inf")),
    ],
)
def test_sweep_reconstructs_and_rejects_unchecked_power_roots(field: str, value: Any) -> None:
    corrupt = PowerCalibration.model_validate(payload()).model_copy(update={field: value})
    with pytest.raises(ValidationError):
        collect_power_sweep([corrupt])


@pytest.mark.parametrize("detected,clear", [(0, 0), (1, 0), (1, 1), (2, 0), (2, 2)])
def test_power_coherent_boundary_counts_and_numeric_scalars_remain_valid(
    detected: int, clear: int
) -> None:
    root = PowerCalibration.model_validate(
        payload()
        | {
            "n_symbols": np.int64(2),
            "n_detected": np.int32(detected),
            "n_clear_deflation_bar": np.int64(clear),
            "detection_rate": Fraction(detected, 2),
            "deflation_bar": np.float32(0.0),
        }
    )
    assert root.detection_rate == detected / 2
    assert root.n_bars == root.symbol_verdicts == []
    assert root.deflation_bar == 0.0
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root


@given(st.integers(min_value=1, max_value=10000), st.integers(min_value=0, max_value=10000))
def test_power_coherent_count_ratio_round_trips(searched: int, draw: int) -> None:
    detected = draw % (searched + 1)
    root = PowerCalibration.model_validate(
        payload()
        | {
            "n_symbols": searched,
            "n_detected": detected,
            "n_clear_deflation_bar": detected,
            "detection_rate": detected / searched,
        }
    )
    assert 0 <= root.n_clear_deflation_bar <= root.n_detected <= root.n_symbols
    assert root.detection_rate == detected / searched
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root
