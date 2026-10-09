"""Validate present legacy elements without inventing missing observations."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import NullCalibration, merge_calibrations
from app.research.lab.universe import expected_max_sharpe_under_null

SCORES = [
    "walk_forward_oos_sharpes",
    "walk_forward_hold_sharpes",
    "purged_cv_oos_sharpes",
    "purged_cv_hold_sharpes",
]


def payload() -> dict[str, Any]:
    return {
        "n_symbols": 1,
        "n_graduates": 0,
        "false_graduation_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "max_deflated_sharpe": -0.1,
        "max_holdout_sharpe": None,
        "graduates": [],
        "holdout_years": [5.0],
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("field", SCORES)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False, "0.5"])
def test_present_legacy_scores_require_original_finite_real_evidence(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {field: [value]})


@pytest.mark.parametrize(
    "value",
    [0, -1, float("nan"), float("inf"), -float("inf"), True, False, "5", Fraction(1, 10**400)],
)
def test_present_holdout_years_require_positive_finite_original_evidence(value: object) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {"holdout_years": [value]})


@pytest.mark.parametrize("value", [0, -1, True, False, 1.0, "1"])
def test_present_bar_counts_require_positive_original_integers(value: object) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {"n_bars": [value]})


@pytest.mark.parametrize("field", SCORES)
def test_json_loading_rejects_nonfinite_array_evidence(field: str) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate_json(json.dumps(payload() | {field: [float("nan")]}))


@pytest.mark.parametrize(
    "field,value", [(f, float("inf")) for f in SCORES] + [("holdout_years", 0.0), ("n_bars", 0)]
)
def test_merge_rejects_unchecked_invalid_array_copies(field: str, value: object) -> None:
    root = NullCalibration.model_validate(payload()).model_copy(update={field: [value]})
    with pytest.raises(ValidationError):
        merge_calibrations([root])


@pytest.mark.parametrize("field", SCORES)
@pytest.mark.parametrize("value", [-2.0, 0.0, np.float32(0.5), Fraction(-1, 3)])
def test_valid_signed_numeric_score_elements_remain_supported(
    field: str, value: float | Fraction
) -> None:
    root = NullCalibration.model_validate(payload() | {field: (value,)})
    assert getattr(root, field) == [float(value)]


def test_positive_numpy_history_and_fraction_years_remain_supported() -> None:
    root = NullCalibration.model_validate(
        payload() | {"n_bars": [np.int64(1260)], "holdout_years": [Fraction(1, 3)]}
    )
    assert root.n_bars == [1260]
    assert root.holdout_years == [1 / 3]


def test_legacy_empty_arrays_remain_unmeasured() -> None:
    root = NullCalibration.model_validate(payload())
    assert root.n_bars == root.symbol_diagnostics == []
    assert all(getattr(root, field) == [] for field in SCORES)
    assert root.walk_forward_null_percentiles is None
    assert root.paired_excess(SCORES[0], SCORES[1]) is None


def test_partial_legacy_arrays_remain_raw_measurements_without_excess_pairing() -> None:
    root = NullCalibration.model_validate(
        payload()
        | {
            "n_symbols": 2,
            "holdout_years": [5.0, 5.0],
            "deflation_bar": expected_max_sharpe_under_null(2, 5.0),
            SCORES[0]: [0.5],
            SCORES[1]: [0.2],
        }
    )
    assert root.walk_forward_null_percentiles == (0.5, 0.5, 0.5)
    assert root.paired_excess(SCORES[0], SCORES[1]) is None
