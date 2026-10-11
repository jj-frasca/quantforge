"""Capture headers must describe their nested evidence (ADR-247)."""

from statistics import median

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import (
    PowerCalibration,
    PowerSweep,
    collect_power_sweep,
    compare_power_sweeps,
)


def cell(version: str, history: list[int], *, key: float = 0.2) -> PowerCalibration:
    return PowerCalibration(
        n_symbols=2,
        n_detected=0,
        detection_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.0,
        phi=key,
        oracle_sharpes=[1.0, 1.0],
        net_oracle_sharpes=[1.0, 1.0],
        finalist_observed_sharpes=[0.5 if version == "before" else 1.0] * 2,
        finalist_strategy_names=[version] * 2,
        holdout_years=[4.0, 4.0],
        n_bars=history,
        errors={},
        gate_config_version="gate",
        search_config_version=version,
    )


@pytest.mark.parametrize("side", ["before", "after"])
@pytest.mark.parametrize(
    "field", ["edge", "gate_config_version", "search_config_version", "n_bars"]
)
@pytest.mark.parametrize("persisted", [False, True])
def test_nested_identity_refuses_mislabeled_cell(side: str, field: str, persisted: bool) -> None:
    before = collect_power_sweep([cell("before", [7400])])
    after = collect_power_sweep([cell("after", [7400])])
    target = before if side == "before" else after
    nested = target.cells[0].model_dump(round_trip=True)
    nested[field] = {
        "edge": "band_reversion",
        "gate_config_version": "another-gate",
        "search_config_version": "after" if side == "before" else "before",
        "n_bars": [9247],
    }[field]
    wrapper = target.model_dump(round_trip=True)
    wrapper["cells"] = [nested]
    malformed = PowerSweep.model_validate(wrapper)
    if persisted:
        malformed = PowerSweep.model_validate_json(malformed.model_dump_json(round_trip=True))
    before, after = (malformed, after) if side == "before" else (before, malformed)
    with pytest.raises(ValueError, match=field):
        compare_power_sweeps(before, after)


@pytest.mark.parametrize("side", ["before", "after"])
def test_all_absent_histories_require_existing_zero_marker(side: str) -> None:
    before = collect_power_sweep([cell("before", [] if side == "before" else [7400])])
    after = collect_power_sweep([cell("after", [] if side == "after" else [7400])])
    before = before.model_copy(update={"n_bars": 7400})
    after = after.model_copy(update={"n_bars": 7400})
    with pytest.raises(ValueError, match=r"n_bars|history"):
        compare_power_sweeps(before, after)


def test_each_recorded_cell_history_must_match_header() -> None:
    before = collect_power_sweep([cell("before", [7400]), cell("before", [7400], key=0.4)])
    after = collect_power_sweep([cell("after", [7400]), cell("after", [7400], key=0.4)])
    wrapper = after.model_dump(round_trip=True)
    wrapper["cells"] = [cell("after", [7400]), cell("after", [9247], key=0.4)]
    with pytest.raises(ValueError, match="n_bars"):
        compare_power_sweeps(before, PowerSweep.model_validate(wrapper))


def test_unrepresentable_native_history_summary_refuses_as_history_evidence() -> None:
    before = PowerSweep(
        edge="ar1",
        gate_config_version="gate",
        search_config_version="before",
        n_bars=10**400,
        cells=[cell("before", [10**400, 10**400])],
    )
    after = PowerSweep(
        edge="ar1",
        gate_config_version="gate",
        search_config_version="after",
        n_bars=10**400,
        cells=[cell("after", [10**400, 10**400])],
    )
    with pytest.raises(ValueError, match="history"):
        compare_power_sweeps(before, after)


@pytest.mark.parametrize("history", [[7400], [7400, 7401], [7399, 7400, 7401], [10**310]])
def test_native_descriptive_history_summaries_remain_supported(history: list[int]) -> None:
    before = collect_power_sweep([cell("before", history)])
    after = collect_power_sweep([cell("after", history)])
    assert before.n_bars == int(median(history))
    row = compare_power_sweeps(before, after)[0]
    assert row.capture_delta == 0.5
    assert row.net_capture_delta == 0.5
    assert row.attributable is True


def test_mixed_recorded_and_absent_histories_preserve_legacy_rows() -> None:
    before = collect_power_sweep([cell("before", [7400]), cell("before", [], key=0.4)])
    after = collect_power_sweep([cell("after", [7400]), cell("after", [], key=0.4)])
    rows = compare_power_sweeps(before, after)
    assert [row.key for row in rows] == [0.2, 0.4]
    assert rows[0].net_capture_delta == 0.5
    assert rows[1].net_capture_delta is None
    assert rows[1].capture_delta == 0.5


def test_all_absent_histories_keep_zero_header_and_gross_comparison() -> None:
    row = compare_power_sweeps(
        collect_power_sweep([cell("before", [])]), collect_power_sweep([cell("after", [])])
    )[0]
    assert row.net_capture_delta is None
    assert row.capture_delta == 0.5


def test_direct_empty_sweeps_keep_existing_comparison_behavior() -> None:
    before = collect_power_sweep([cell("before", [7400])]).model_copy(update={"cells": []})
    after = collect_power_sweep([cell("after", [7400])])
    rows = compare_power_sweeps(before, after)
    assert len(rows) == 1
    assert rows[0].capture_delta is None
    assert rows[0].attributable is False
    assert compare_power_sweeps(before, after.model_copy(update={"cells": []})) == []


def test_existing_wrapper_refusal_precedes_nested_binding() -> None:
    before = collect_power_sweep([cell("before", [7400])])
    after = collect_power_sweep([cell("after", [9247])]).model_copy(update={"edge": "other"})
    with pytest.raises(ValueError, match="different edge"):
        compare_power_sweeps(before, after)


@given(st.lists(st.integers(7400, 7500), min_size=1, max_size=5))
def test_collector_history_contract_preserves_capture_comparison(history: list[int]) -> None:
    row = compare_power_sweeps(
        collect_power_sweep([cell("before", history)]),
        collect_power_sweep([cell("after", history)]),
    )[0]
    assert row.capture_delta == 0.5
    assert row.net_capture_delta == 0.5
