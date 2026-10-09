"""Intrinsic root evidence and count claims must survive authoritative reconstruction."""

from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import NullCalibration, merge_calibrations


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


@pytest.mark.parametrize("field", ["n_symbols", "n_graduates", "n_clear_deflation_bar"])
@pytest.mark.parametrize("value", [-1, True, False, 0.0, 1.0, "0", "1"])
def test_root_rejects_invalid_original_counts(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {field: value})


def test_root_requires_a_positive_searched_denominator() -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {"n_symbols": 0})


@pytest.mark.parametrize(
    "field", ["false_graduation_rate", "deflation_bar", "max_deflated_sharpe", "max_holdout_sharpe"]
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False, "0.5"])
def test_root_rejects_invalid_original_scores(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {field: value})


@pytest.mark.parametrize("value", [-0.1, 1.1, Fraction(2**54 + 1, 2**54), Fraction(-1, 10**400)])
def test_root_rate_bounds_apply_before_rounding(value: object) -> None:
    claim = payload()
    if isinstance(value, Fraction) and value > 1:
        # Keep the rounded 1.0 rate coherent: only original bounds may reject it.
        claim.update(
            n_graduates=1,
            max_holdout_sharpe=0.5,
            graduates=[
                {
                    "symbol": "N",
                    "holdout_sharpe": 0.5,
                    "holdout_n_bars": 1260,
                    "deflated_sharpe": 0.1,
                }
            ],
        )
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(claim | {"false_graduation_rate": value})


@pytest.mark.parametrize("value", [-0.1, Fraction(-1, 10**400)])
def test_root_deflation_bar_is_nonnegative_before_rounding(value: object) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | {"deflation_bar": value})


@pytest.mark.parametrize(
    "update",
    [
        {"n_graduates": 1, "false_graduation_rate": 1.0},
        {"n_clear_deflation_bar": 1},
        {"false_graduation_rate": 0.5},
    ],
)
def test_root_rejects_incoherent_count_claims(update: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(payload() | update)


def test_merge_rejects_unchecked_nonfinite_root_maximum() -> None:
    root = NullCalibration.model_validate(payload()).model_copy(
        update={"max_deflated_sharpe": float("inf")}
    )
    with pytest.raises(ValidationError):
        merge_calibrations([root])


@pytest.mark.parametrize("value", [-2.0, 0.0, np.float64(1.0), Fraction(-1, 3)])
def test_valid_signed_maxima_and_legacy_absence_remain_supported(value: float | Fraction) -> None:
    root = NullCalibration.model_validate(
        payload() | {"n_symbols": np.int64(1), "max_deflated_sharpe": value}
    )
    assert root.max_deflated_sharpe == float(value)
    assert root.n_graduates == root.n_clear_deflation_bar == 0
    assert root.max_holdout_sharpe is None
    assert root.n_bars == root.symbol_diagnostics == []


def test_a_coherent_full_graduation_rate_and_signed_holdout_maximum_remain_valid() -> None:
    graduate = {
        "symbol": "N",
        "holdout_sharpe": -0.5,
        "holdout_n_bars": 1260,
        "deflated_sharpe": 0.1,
    }
    root = NullCalibration.model_validate(
        payload()
        | {
            "n_graduates": 1,
            "false_graduation_rate": 1.0,
            "graduates": [graduate],
            "max_holdout_sharpe": -0.5,
        }
    )
    assert root.false_graduation_rate == 1.0
