"""Derived excess must remain representable even when its two operands are finite."""

from typing import Any

import pytest

from app.research.lab.calibration import NullCalibration

PAIRS = [
    ("walk_forward_oos_sharpes", "walk_forward_hold_sharpes"),
    ("purged_cv_oos_sharpes", "purged_cv_hold_sharpes"),
]


def calibration(
    paired: bool, fields: tuple[str, str], left: float, right: float
) -> NullCalibration:
    oos, hold = fields
    payload: dict[str, Any] = {
        "n_symbols": 1,
        "n_graduates": 0,
        "false_graduation_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "max_deflated_sharpe": 0.0,
        "max_holdout_sharpe": None,
        "graduates": [],
        "holdout_years": [5.0],
        "n_bars": [6300],
        "errors": {},
        "gate_config_version": "gate",
        oos: [left],
        hold: [right],
    }
    if paired:
        payload["symbol_diagnostics"] = [
            {
                "symbol": "N",
                "n_bars": 6300,
                "holdout_years": 5.0,
                oos.removesuffix("s"): left,
                hold.removesuffix("s"): right,
            }
        ]
    return NullCalibration.model_validate(payload)


@pytest.mark.parametrize("paired", [False, True])
@pytest.mark.parametrize("fields", PAIRS)
@pytest.mark.parametrize("sign", [-1, 1])
def test_finite_operands_with_overflowing_excess_fail_closed(
    paired: bool, fields: tuple[str, str], sign: int
) -> None:
    result = calibration(paired, fields, sign * 1e308, -sign * 1e308)
    with pytest.raises(ValueError, match="finite"):
        result.paired_excess(*fields)


@pytest.mark.parametrize("paired", [False, True])
@pytest.mark.parametrize("fields", PAIRS)
@pytest.mark.parametrize("left,right,expected", [(1.5, 2.0, -0.5), (-2.0, -2.0, 0.0)])
def test_signed_and_zero_finite_excess_are_preserved(
    paired: bool, fields: tuple[str, str], left: float, right: float, expected: float
) -> None:
    assert calibration(paired, fields, left, right).paired_excess(*fields) == [expected]


@pytest.mark.parametrize("paired", [False, True])
@pytest.mark.parametrize("fields", PAIRS)
def test_missing_pair_remains_unmeasured(paired: bool, fields: tuple[str, str]) -> None:
    result = calibration(paired, fields, 1.0, 0.5)
    payload = result.model_dump(round_trip=True)
    payload[fields[1]] = []
    if paired:
        payload["symbol_diagnostics"][0][fields[1].removesuffix("s")] = None
    incomplete = NullCalibration.model_validate(payload)
    assert incomplete.paired_excess(*fields) is None
