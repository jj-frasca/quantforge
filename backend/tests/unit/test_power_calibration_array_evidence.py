"""Present power observations cannot be silently coerced into evidence."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import PowerCalibration, collect_power_sweep

SCORES = [
    "oracle_sharpes",
    "net_oracle_sharpes",
    "achievable_oracle_sharpes",
    "finalist_observed_sharpes",
]


def payload() -> dict[str, Any]:
    return {
        "n_symbols": 2,
        "n_detected": 0,
        "detection_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "phi": 0.3,
        "oracle_sharpes": [],
        "holdout_years": [5.0, 5.0],
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("field", SCORES)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False, "0.5"])
def test_present_power_scores_require_original_finite_real_evidence(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {field: [value]})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False, "0.5"])
def test_category_scores_require_original_finite_real_evidence(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(
            payload() | {"finalist_sharpes_by_category": {"Trend": [value]}}
        )


@pytest.mark.parametrize("value", [0, -1, True, False, 1.0, "1"])
def test_power_bar_elements_require_original_positive_integers(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {"n_bars": [value]})


@pytest.mark.parametrize(
    "value", [0.0, -1.0, True, "5", float("nan"), float("inf"), Fraction(1, 10**400)]
)
def test_power_year_elements_require_original_positive_finite_reals(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(payload() | {"holdout_years": [value]})


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        True,
        False,
        "0.5",
        -0.1,
        1.1,
        Fraction(10**400 + 1, 10**400),
        Fraction(-1, 10**400),
    ],
)
def test_power_probability_elements_validate_original_bounds(value: Any) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate(
            payload() | {"finalist_deflated_sharpe_probabilities": [value]}
        )


@pytest.mark.parametrize("field", SCORES)
def test_power_json_rejects_nonfinite_score_arrays(field: str) -> None:
    with pytest.raises(ValidationError):
        PowerCalibration.model_validate_json(json.dumps(payload() | {field: [float("nan")]}))


@pytest.mark.parametrize(
    "field,value",
    [(field, [float("inf")]) for field in SCORES]
    + [
        ("n_bars", [0]),
        ("holdout_years", [0.0]),
        ("finalist_deflated_sharpe_probabilities", [True]),
        ("finalist_sharpes_by_category", {"Trend": [float("inf")]}),
    ],
)
def test_sweep_rejects_unchecked_invalid_power_arrays(field: str, value: Any) -> None:
    root = PowerCalibration.model_validate(payload()).model_copy(update={field: value})
    with pytest.raises(ValidationError):
        collect_power_sweep([root])


@pytest.mark.parametrize("field", SCORES)
@pytest.mark.parametrize("value", [-2.0, 0.0, np.float32(0.5), Fraction(-1, 3)])
def test_power_signed_numeric_score_elements_remain_supported(field: str, value: Any) -> None:
    root = PowerCalibration.model_validate(payload() | {field: (value,)})
    assert getattr(root, field) == [float(value)]


def test_power_history_probability_category_numeric_scalars_remain_supported() -> None:
    root = PowerCalibration.model_validate(
        payload()
        | {
            "n_bars": (np.int64(1260),),
            "holdout_years": (Fraction(1, 3),),
            "finalist_deflated_sharpe_probabilities": (None, 0.0, Fraction(1, 2), np.float64(1.0)),
            "finalist_sharpes_by_category": {"Trend": (Fraction(-1, 3), 0.0)},
        }
    )
    assert root.n_bars == [1260] and root.holdout_years == [1 / 3]
    assert root.finalist_deflated_sharpe_probabilities == [None, 0.0, 0.5, 1.0]
    assert root.finalist_sharpes_by_category == {"Trend": [-1 / 3, 0.0]}
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root


def test_power_empty_and_partial_legacy_arrays_preserve_refusal_semantics() -> None:
    empty = PowerCalibration.model_validate(payload())
    assert empty.n_bars == empty.finalist_deflated_sharpe_probabilities == []
    assert empty.oracle_sharpe_percentiles is None and empty.capture_ratio is None
    partial = PowerCalibration.model_validate(
        payload() | {"oracle_sharpes": [2.0], "finalist_observed_sharpes": [1.0]}
    )
    assert partial.oracle_sharpe_percentiles == (2.0, 2.0, 2.0)
    assert partial.capture_ratio is None
