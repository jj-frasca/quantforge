"""Complete null joint verdicts and the advertised graduate claim agree (ADR-224)."""

import json
from math import log, sqrt
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    NullCalibration,
    NullSymbolDiagnostics,
    merge_calibrations,
)
from app.research.lab.gate import GateResult


def verdict(
    symbol: str, *, score: float = 0.0, bars: int = 252, passed: bool = True
) -> CalibrationSymbolVerdict:
    return CalibrationSymbolVerdict(
        symbol=symbol,
        deflated_sharpe_probability=None,
        holdout_sharpe=score,
        holdout_n_bars=bars,
        gate_result=GateResult(
            passed=passed,
            dsr_ok=passed,
            pbo_ok=True,
            stability_ok=True,
            mintrl_ok=True,
            holdout_ok=True,
            beats_buy_and_hold_ok=True,
            required_track_record_years=1.0,
            gate_config_version="gate",
            holdout_sharpe=score,
            holdout_n_bars=bars,
        ),
    )


def payload(records: list[CalibrationSymbolVerdict]) -> dict[str, Any]:
    diagnostics = [
        NullSymbolDiagnostics(
            symbol=r.symbol,
            n_bars=7400,
            holdout_years=r.holdout_n_bars / 252,
            calibration_verdict=r,
        ).model_dump(mode="json")
        for r in records
    ]
    graduates = [
        {
            "symbol": r.symbol,
            "holdout_sharpe": r.holdout_sharpe,
            "holdout_n_bars": r.holdout_n_bars,
            "deflated_sharpe": 0.25,
        }
        for r in records
        if r.gate_result.passed
    ]
    return {
        "n_symbols": len(records),
        "n_graduates": len(graduates),
        "false_graduation_rate": len(graduates) / len(records),
        "n_clear_deflation_bar": sum(
            r.gate_result.passed
            and r.holdout_sharpe > sqrt(2 * log(len(records)) / (r.holdout_n_bars / 252))
            for r in records
        ),
        "deflation_bar": 0.0,
        "max_deflated_sharpe": 10.0,
        "max_holdout_sharpe": None,
        "graduates": graduates,
        "holdout_years": [d["holdout_years"] for d in diagnostics],
        "n_bars": [7400] * len(records),
        "symbol_diagnostics": diagnostics,
        "errors": {},
        "gate_config_version": "gate",
    }


def contradictions() -> list[dict[str, Any]]:
    base = payload([verdict("A", score=2.0)])
    return [
        base
        | {
            "n_graduates": 0,
            "false_graduation_rate": 0.0,
            "graduates": [],
            "n_clear_deflation_bar": 0,
        },
        base | {"n_clear_deflation_bar": 0},
        base | {"graduates": [base["graduates"][0] | {"symbol": "UNSEARCHED"}]},
        base | {"graduates": [base["graduates"][0] | {"holdout_sharpe": -2.0}]},
        base | {"graduates": [base["graduates"][0] | {"holdout_n_bars": 504}]},
        payload([verdict("A", passed=False)])
        | {"n_graduates": 1, "false_graduation_rate": 1.0, "graduates": base["graduates"]},
    ]


@pytest.mark.parametrize("data", contradictions())
@pytest.mark.parametrize("channel", ["direct", "json"])
def test_modern_null_rejects_joint_graduate_contradictions(
    data: dict[str, Any], channel: str
) -> None:
    with pytest.raises(ValidationError):
        if channel == "json":
            NullCalibration.model_validate_json(json.dumps(data))
        else:
            NullCalibration.model_validate(data)


def test_duplicate_graduates_cannot_replace_a_passing_symbol() -> None:
    data = payload([verdict("A"), verdict("B")])
    data["graduates"][1] = data["graduates"][0]
    with pytest.raises(ValidationError):
        NullCalibration.model_validate(data)


@pytest.mark.parametrize("score,survivors", [(-1.0, 0), (0.0, 0), (1.0, 1)])
def test_null_survival_retains_strict_bar_boundary(score: float, survivors: int) -> None:
    root = NullCalibration.model_validate(payload([verdict("A", score=score)]))
    assert root.n_clear_deflation_bar == survivors


def test_null_survival_uses_own_history_and_only_incumbent_passers() -> None:
    records = [
        verdict("short", score=1.0),
        verdict("long", score=1.0, bars=1008),
        verdict("failed", score=100.0, passed=False),
    ]
    data = payload(records)
    root = NullCalibration.model_validate(data)
    assert root.n_clear_deflation_bar == 1
    for wrong in [0, 2]:
        with pytest.raises(ValidationError):
            NullCalibration.model_validate(data | {"n_clear_deflation_bar": wrong})


def test_nullable_probability_and_graduate_order_freedom_remain() -> None:
    data = payload([verdict("A"), verdict("B")])
    data["graduates"].reverse()
    root = NullCalibration.model_validate(data)
    assert root.graduate_symbols == ["B", "A"]
    assert root.max_deflated_sharpe == 10.0
    assert [g.deflated_sharpe for g in root.graduates] == [0.25, 0.25]
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root


@pytest.mark.parametrize("diagnostics", [False, True])
def test_absent_legacy_joints_retain_prior_claim_semantics(diagnostics: bool) -> None:
    data = contradictions()[0]
    if diagnostics:
        data["symbol_diagnostics"][0]["calibration_verdict"] = None
    else:
        data["symbol_diagnostics"] = []
    root = NullCalibration.model_validate(data)
    assert root.n_graduates == 0 and root.n_clear_deflation_bar == 0


@pytest.mark.parametrize("index", [0, 1, 2, 3, 4])
def test_merge_reconstructs_and_rejects_unchecked_modern_null_claim(index: int) -> None:
    root = NullCalibration.model_validate(payload([verdict("A", score=2.0)]))
    bad = root.model_copy(update=contradictions()[index])
    with pytest.raises(ValidationError):
        merge_calibrations([bad])


def test_native_merge_rejudges_joint_survival_at_combined_n() -> None:
    left = NullCalibration.model_validate(payload([verdict("A", score=0.5)]))
    right = NullCalibration.model_validate(payload([verdict("B", score=0.5)]))
    assert left.n_clear_deflation_bar == right.n_clear_deflation_bar == 1
    merged = merge_calibrations([left, right])
    assert merged.n_graduates == 2 and merged.n_clear_deflation_bar == 0


@given(
    st.lists(
        st.tuples(
            st.floats(-5, 5, allow_nan=False, allow_infinity=False),
            st.integers(2, 3000),
            st.booleans(),
        ),
        min_size=1,
        max_size=8,
    )
)
def test_coherent_null_joint_counts_round_trip_with_independent_own_history_bar(
    rows: list[tuple[float, int, bool]],
) -> None:
    records = [verdict(str(i), score=s, bars=b, passed=p) for i, (s, b, p) in enumerate(rows)]
    data = payload(records)
    root = NullCalibration.model_validate(data)
    assert root.n_graduates == sum(p for _, _, p in rows)
    assert root.n_clear_deflation_bar == sum(
        p and s > sqrt(2 * log(len(rows)) * 252 / b) for s, b, p in rows
    )
    assert NullCalibration.model_validate_json(root.model_dump_json()) == root
