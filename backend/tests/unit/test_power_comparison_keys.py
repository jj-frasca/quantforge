"""File order cannot select paired capture evidence (ADR-246)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import (
    PowerCalibration,
    collect_power_sweep,
    compare_power_sweeps,
)


def cell(
    version: str,
    score: float,
    *,
    phi: float | None = 0.2,
    half_life: float | None = None,
    edge: str = "ar1",
) -> PowerCalibration:
    return PowerCalibration(
        n_symbols=1,
        n_detected=0,
        detection_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.0,
        edge=edge,
        phi=phi,
        half_life=half_life,
        oracle_sharpes=[1.0],
        net_oracle_sharpes=[1.0],
        finalist_observed_sharpes=[score],
        finalist_strategy_names=[version],
        holdout_years=[4.0],
        n_bars=[7400],
        errors={},
        gate_config_version="gate",
        search_config_version=version,
    )


@pytest.mark.parametrize("side", ["before", "after"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("kind", ["ar1", "band", "zero", "legacy", "identical"])
def test_duplicate_effect_identity_refuses_before_cell_selection(
    side: str, reverse: bool, kind: str
) -> None:
    if kind == "band":
        left = cell(side, 0.5, phi=None, half_life=4.0, edge="band_reversion")
        right = cell(side, 1.5, phi=None, half_life=4.0, edge="band_reversion")
    elif kind == "zero":
        left = cell(side, 0.5, phi=-0.0)
        right = cell(side, 1.5, phi=0.0)
    elif kind == "legacy":
        left = cell(side, 0.5, phi=None)
        right = cell(side, 1.5, phi=None, half_life=0.0)
    else:
        left = cell(side, 0.5)
        right = cell(side, 0.5 if kind == "identical" else 1.5)
    duplicates = [right, left] if reverse else [left, right]
    other_version = "after" if side == "before" else "before"
    other = collect_power_sweep(
        [cell(other_version, 1.0, phi=left.phi, half_life=left.half_life, edge=left.edge)]
    )
    ambiguous = collect_power_sweep(duplicates)
    before, after = (ambiguous, other) if side == "before" else (other, ambiguous)
    with pytest.raises(ValueError, match="duplicate"):
        compare_power_sweeps(before, after)


def test_existing_search_identity_refusal_keeps_precedence() -> None:
    ambiguous = collect_power_sweep([cell("same", 0.5), cell("same", 1.5)])
    with pytest.raises(ValueError, match="same search_config_version"):
        compare_power_sweeps(ambiguous, ambiguous)


def test_distinct_keys_preserve_sorted_union_and_unmatched_evidence() -> None:
    before = collect_power_sweep([cell("before", 0.5, phi=-0.2), cell("before", 0.5)])
    after = collect_power_sweep([cell("after", 1.0), cell("after", 1.0, phi=0.4)])
    rows = compare_power_sweeps(before, after)
    assert [row.key for row in rows] == [-0.2, 0.2, 0.4]
    for row in (rows[0], rows[2]):
        assert row.capture_delta is None
        assert row.net_capture_delta is None
        assert row.attributable is False
    assert rows[1].capture_delta == 0.5
    assert rows[1].net_capture_delta == 0.5
    assert rows[1].attributable is True


@given(st.lists(st.integers(-10, 10), min_size=1, max_size=6, unique=True))
def test_unique_cell_input_order_preserves_complete_comparison_rows(keys: list[int]) -> None:
    before_cells = [cell("before", 0.5, phi=float(key)) for key in keys]
    after_cells = [cell("after", 1.0, phi=float(key)) for key in keys]
    rows = compare_power_sweeps(collect_power_sweep(before_cells), collect_power_sweep(after_cells))
    reversed_rows = compare_power_sweeps(
        collect_power_sweep(before_cells[::-1]), collect_power_sweep(after_cells[::-1])
    )
    assert [row.model_dump_json() for row in rows] == [
        row.model_dump_json() for row in reversed_rows
    ]
    assert [row.key for row in rows] == sorted(keys)
