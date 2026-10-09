"""Displayed null benchmarks describe all searched histories (ADR-227)."""

import json
from math import isfinite, log, sqrt
from statistics import median
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import NullCalibration, merge_calibrations
from app.research.lab.universe import expected_max_sharpe_under_null


def payload(years: list[float], *, n: int | None = None) -> dict[str, Any]:
    searched = n if n is not None else len(years)
    return {
        "n_symbols": searched,
        "n_graduates": 0,
        "false_graduation_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": expected_max_sharpe_under_null(searched, median(years)) if years else 7.0,
        "max_deflated_sharpe": -1.0,
        "max_holdout_sharpe": None,
        "graduates": [],
        "holdout_years": years,
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("years", [[1.0], [1.0, 3.0], [1.0, 2.0, 9.0]])
@pytest.mark.parametrize("wrong", [0.1, 10.0])
@pytest.mark.parametrize("channel", ["root", "json", "merge"])
def test_complete_searched_history_refuses_false_displayed_bar(
    years: list[float],
    wrong: float,
    channel: str,
) -> None:
    data = payload(years)
    original = NullCalibration.model_validate(data)
    data["deflation_bar"] = wrong
    with pytest.raises(ValidationError, match="deflation_bar"):
        if channel == "root":
            NullCalibration.model_validate(data)
        elif channel == "json":
            NullCalibration.model_validate_json(json.dumps(data))
        else:
            merge_calibrations([original.model_copy(update={"deflation_bar": wrong})])


@pytest.mark.parametrize("years", [[1e308, 1e308], [1e-320, 1e-320]])
@pytest.mark.parametrize("channel", ["root", "json", "merge"])
def test_nonfinite_derived_history_or_bar_cannot_be_reported_as_zero(
    years: list[float],
    channel: str,
) -> None:
    data = payload([1.0, 1.0])
    original = NullCalibration.model_validate(data)
    data.update(holdout_years=years, deflation_bar=0.0)
    with pytest.raises(ValidationError, match="deflation_bar"):
        if channel == "root":
            NullCalibration.model_validate(data)
        elif channel == "json":
            NullCalibration.model_validate_json(json.dumps(data))
        else:
            merge_calibrations(
                [
                    original.model_copy(
                        update={
                            "holdout_years": years,
                            "deflation_bar": 0.0,
                        }
                    )
                ]
            )


@pytest.mark.parametrize("years", [[], [2.0]])
def test_incomplete_legacy_history_does_not_invent_displayed_bar(years: list[float]) -> None:
    data = payload(years, n=3) | {"deflation_bar": 7.0}
    root = NullCalibration.model_validate(data)
    assert root.deflation_bar == 7.0
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root


@pytest.mark.parametrize("years", [[1.0], [1e308], [1.0, 3.0], [1.0, 2.0, 9.0]])
def test_exact_complete_history_bar_round_trips(years: list[float]) -> None:
    root = NullCalibration.model_validate(payload(years))
    assert isfinite(root.deflation_bar)
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root
    assert merge_calibrations([root]) == root


def test_merge_recomputes_displayed_bar_at_combined_n_and_all_searched_years() -> None:
    left = NullCalibration.model_validate(payload([1.0]))
    right = NullCalibration.model_validate(payload([4.0]))
    merged = merge_calibrations([left, right])
    assert left.deflation_bar == right.deflation_bar == 0.0
    assert merged.deflation_bar == expected_max_sharpe_under_null(2, 2.5)
    assert merged.n_graduates == merged.n_clear_deflation_bar == 0


@given(
    st.lists(
        st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=15,
    )
)
def test_complete_history_bar_uses_median_searched_years(years: list[float]) -> None:
    root = NullCalibration.model_validate(payload(years))
    expected = sqrt(2 * log(len(years)) / median(years)) if len(years) > 1 else 0.0
    assert root.deflation_bar == pytest.approx(expected, rel=1e-14)
