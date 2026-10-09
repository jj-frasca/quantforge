"""Known graduate identity must be unambiguous even without joints (ADR-228)."""

import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import NullCalibration, merge_calibrations
from app.research.lab.universe import expected_max_sharpe_under_null


def payload(symbols: list[str], scores: list[float]) -> dict[str, Any]:
    n = max(1, len(symbols))
    bar = expected_max_sharpe_under_null(n, 4.0)
    return {
        "n_symbols": n,
        "n_graduates": len(symbols),
        "false_graduation_rate": len(symbols) / n,
        "n_clear_deflation_bar": sum(score > bar for score in scores),
        "deflation_bar": bar,
        "max_deflated_sharpe": 100.0,
        "max_holdout_sharpe": max(scores, default=None),
        "graduates": [
            {
                "symbol": symbol,
                "holdout_sharpe": score,
                "holdout_n_bars": 1008,
                "deflated_sharpe": -1.0,
            }
            for symbol, score in zip(symbols, scores, strict=True)
        ],
        "holdout_years": [4.0] * n,
        "errors": {},
        "gate_config_version": "gate",
    }


@pytest.mark.parametrize("scores", [[2.0, 2.0], [2.0, 3.0], [-2.0, -3.0]])
@pytest.mark.parametrize("channel", ["root", "json", "single", "unchecked"])
def test_legacy_duplicate_graduate_identities_are_refused(
    scores: list[float], channel: str
) -> None:
    original = NullCalibration.model_validate(payload(["A", "B"], scores))
    data = payload(["A", "A"], scores)
    with pytest.raises(ValidationError, match="duplicate graduate"):
        if channel == "root":
            NullCalibration.model_validate(data)
        elif channel == "json":
            NullCalibration.model_validate_json(json.dumps(data))
        elif channel == "single":
            merge_calibrations([original.model_copy(update={"graduates": data["graduates"]})])
        else:
            copied = original.graduates[1].model_copy(update={"symbol": "A"})
            merge_calibrations(
                [
                    original.model_copy(
                        update={
                            "graduates": [original.graduates[0], copied],
                        }
                    )
                ]
            )


def test_merge_refuses_collision_between_individually_valid_legacy_shards() -> None:
    left = NullCalibration.model_validate(payload(["A"], [2.0]))
    right = NullCalibration.model_validate(payload(["A"], [3.0]))
    with pytest.raises(ValidationError, match="duplicate graduate"):
        merge_calibrations([left, right])


@pytest.mark.parametrize("symbols,scores", [([], []), (["A"], [2.0]), (["B", "A"], [2.0, -3.0])])
def test_empty_and_distinct_legacy_graduates_keep_order_and_counts(
    symbols: list[str],
    scores: list[float],
) -> None:
    root = NullCalibration.model_validate(payload(symbols, scores))
    assert not root.symbol_diagnostics
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root
    assert merge_calibrations([root]) == root
    assert [g.symbol for g in root.graduates] == symbols


def test_distinct_legacy_shards_keep_the_existing_combined_n_judgment() -> None:
    left = NullCalibration.model_validate(payload(["A"], [0.1]))
    right = NullCalibration.model_validate(payload(["B"], [2.0]))
    merged = merge_calibrations([left, right])
    assert merged.n_symbols == merged.n_graduates == 2
    assert merged.false_graduation_rate == 1.0
    assert merged.n_clear_deflation_bar == 1
    assert [g.symbol for g in merged.graduates] == ["A", "B"]


@given(st.lists(st.integers(min_value=0, max_value=100), unique=True, max_size=12))
def test_distinct_known_identities_remain_valid(indices: list[int]) -> None:
    symbols = [f"NULL{i:04d}" for i in indices]
    root = NullCalibration.model_validate(payload(symbols, [2.0] * len(symbols)))
    assert [g.symbol for g in root.graduates] == symbols
