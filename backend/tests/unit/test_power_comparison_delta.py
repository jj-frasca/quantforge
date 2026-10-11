"""Paired capture arithmetic cannot publish infinity as missing evidence (ADR-245)."""

import json
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import (
    PowerCalibration,
    PowerSweep,
    collect_power_sweep,
    compare_power_sweeps,
)


def sweep(
    score: float | None,
    version: str,
    *,
    gross: float = 1.0,
    net: float = 1.0,
    key: float = 0.2,
) -> PowerSweep:
    cell = PowerCalibration(
        n_symbols=1,
        n_detected=0,
        detection_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.0,
        phi=key,
        oracle_sharpes=[gross],
        net_oracle_sharpes=[net],
        finalist_observed_sharpes=[] if score is None else [score],
        finalist_strategy_names=[] if score is None else [version],
        holdout_years=[4.0],
        n_bars=[7400],
        errors={},
        gate_config_version="gate",
        search_config_version=version,
    )
    return collect_power_sweep([cell])


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("gross,net", [(1.0, 1.0), (2.0, 1.0), (1.0, 2.0)])
def test_finite_matched_endpoints_refuse_overflowing_capture_delta(
    sign: float, gross: float, net: float
) -> None:
    before = sweep(-sign * 1e308, "before", gross=gross, net=net)
    after = sweep(sign * 1e308, "after", gross=gross, net=net)
    for cell in (before.cells[0], after.cells[0]):
        assert cell.capture_ratio is not None and math.isfinite(cell.capture_ratio)
        assert cell.net_capture_ratio is not None and math.isfinite(cell.net_capture_ratio)
    with pytest.raises(ValueError, match="delta"):
        compare_power_sweeps(before, after)


@pytest.mark.parametrize(
    "old,new",
    [(0.5, 0.6), (-1e308, 0.0), (0.0, 1e308), (-0.0, 0.0), (0.0, -0.0), (5e-324, 0.0)],
)
def test_finite_native_difference_remains_exact(old: float, new: float) -> None:
    row = compare_power_sweeps(sweep(old, "before"), sweep(new, "after"))[0]
    for actual in (row.net_capture_delta, row.capture_delta):
        assert actual == new - old
        assert math.copysign(1, actual) == math.copysign(1, new - old)
    assert row.attributable is True
    assert row.detection_delta == 0.0
    assert json.loads(row.model_dump_json())["capture_delta"] == new - old


@pytest.mark.parametrize("missing_side", ["before", "after"])
def test_unmeasured_endpoint_keeps_none_instead_of_zero(missing_side: str) -> None:
    before = sweep(None if missing_side == "before" else -1e308, "before")
    after = sweep(None if missing_side == "after" else 1e308, "after")
    row = compare_power_sweeps(before, after)[0]
    assert row.capture_delta is None
    assert row.net_capture_delta is None
    assert row.attributable is False


def test_extreme_unmatched_cells_keep_missing_deltas() -> None:
    rows = compare_power_sweeps(sweep(-1e308, "before", key=0.1), sweep(1e308, "after"))
    assert len(rows) == 2
    for row in rows:
        assert row.capture_delta is None
        assert row.net_capture_delta is None
        assert row.attributable is False


def test_net_noise_refusal_still_allows_finite_gross_difference() -> None:
    row = compare_power_sweeps(sweep(-0.5, "before", net=0.0), sweep(0.5, "after", net=0.0))[0]
    assert row.net_capture_delta is None
    assert row.capture_delta == 1.0


@given(
    st.floats(min_value=-1e150, max_value=1e150, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1e150, max_value=1e150, allow_nan=False, allow_infinity=False),
)
def test_measured_finite_capture_differences_keep_native_subtraction(
    old: float, new: float
) -> None:
    row = compare_power_sweeps(sweep(old, "before"), sweep(new, "after"))[0]
    assert row.capture_delta == new - old
    assert row.net_capture_delta == new - old
