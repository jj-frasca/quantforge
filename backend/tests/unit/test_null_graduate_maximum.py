"""The reported holdout maximum describes graduates, including legacy ones (ADR-226)."""

import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import NullCalibration, merge_calibrations


def payload(scores: list[float]) -> dict[str, Any]:
    n = max(1, len(scores))
    return {
        "n_symbols": n,
        "n_graduates": len(scores),
        "false_graduation_rate": len(scores) / n,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "max_deflated_sharpe": 100.0,
        "max_holdout_sharpe": max(scores, default=None),
        "graduates": [
            {
                "symbol": f"A{i}",
                "holdout_sharpe": score,
                "holdout_n_bars": 252,
                "deflated_sharpe": -1.0,
            }
            for i, score in enumerate(scores)
        ],
        "holdout_years": [1.0] * n,
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize(
    "scores,wrong",
    [
        ([], 10.0),
        ([2.0], None),
        ([2.0], 1.0),
        ([-2.0], 0.0),
        ([-2.0, -3.0], -3.0),
        ([2.0, 2.0], 3.0),
    ],
)
@pytest.mark.parametrize("channel", ["root", "json", "merge"])
def test_contradictory_graduate_maximum_is_refused(
    scores: list[float],
    wrong: float | None,
    channel: str,
) -> None:
    data = payload(scores)
    original = NullCalibration.model_validate(data)
    data["max_holdout_sharpe"] = wrong
    with pytest.raises(ValidationError, match="max_holdout_sharpe"):
        if channel == "root":
            NullCalibration.model_validate(data)
        elif channel == "json":
            NullCalibration.model_validate_json(json.dumps(data))
        else:
            merge_calibrations([original.model_copy(update={"max_holdout_sharpe": wrong})])


@pytest.mark.parametrize("scores", [[], [2.0], [-2.0], [2.0, -3.0], [2.0, 2.0]])
def test_exact_legacy_maximum_round_trips_and_keeps_trial_wide_margin(scores: list[float]) -> None:
    root = NullCalibration.model_validate(payload(scores))
    assert root.max_holdout_sharpe == max(scores, default=None)
    assert root.max_deflated_sharpe == 100.0
    assert not root.symbol_diagnostics
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root
    merged = merge_calibrations([root])
    assert merged.max_holdout_sharpe == root.max_holdout_sharpe
    assert merged.max_deflated_sharpe == 100.0
    assert [g.symbol for g in merged.graduates] == [g.symbol for g in root.graduates]


@given(
    st.lists(
        st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), max_size=12
    )
)
def test_maximum_is_order_independent_and_comes_from_graduates(scores: list[float]) -> None:
    root = NullCalibration.model_validate(payload(scores))
    reversed_root = NullCalibration.model_validate(payload(list(reversed(scores))))
    assert root.max_holdout_sharpe == reversed_root.max_holdout_sharpe == max(scores, default=None)
