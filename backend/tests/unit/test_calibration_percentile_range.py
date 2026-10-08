"""Finite linear quantiles cannot leave the convex hull of finite scores."""

from fractions import Fraction
from math import isfinite
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import NullCalibration, PowerCalibration, _percentiles

MAX_FLOAT = float(np.finfo(float).max)


def rational_quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    left = int(index)
    weight = Fraction.from_float(index - left)
    right = min(left + 1, len(ordered) - 1)
    return float(
        (1 - weight) * Fraction.from_float(ordered[left])
        + weight * Fraction.from_float(ordered[right])
    )


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize(
    "values",
    [
        [1e308, 1e308],
        [-1e308, -1e308],
        [-1e308, 1e308],
        [MAX_FLOAT, MAX_FLOAT],
        [-MAX_FLOAT, -MAX_FLOAT],
        [-MAX_FLOAT, MAX_FLOAT],
    ],
)
def test_extreme_finite_percentiles_recover_representable_quantiles(
    values: list[float], mode: Any
) -> None:
    with np.errstate(all=mode):
        result = _percentiles(values)
    assert result is not None
    assert result == (rational_quantile(values, 0.5), rational_quantile(values, 0.95), max(values))


@pytest.mark.parametrize("values", [[-2.0, 0.0, 1.0, 3.0], [1.0], [0.0, 0.0], [-0.3, 0.1, 0.8]])
def test_measurable_native_percentiles_remain_exact(values: list[float]) -> None:
    assert _percentiles(values) == (
        float(np.median(values)),
        float(np.percentile(values, 95)),
        max(values),
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "1", 1j])
def test_percentile_boundary_rejects_invalid_source_without_filtering(value: Any) -> None:
    with pytest.raises(ValueError):
        _percentiles([0.0, value])


def test_empty_percentiles_remain_unmeasured() -> None:
    assert _percentiles([]) is None


@pytest.mark.parametrize("kind", ["null-walk", "null-purged", "power-gross", "power-net"])
def test_public_calibration_summary_properties_keep_finite_extreme_scores(kind: str) -> None:
    common = {
        "n_symbols": 2,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "holdout_years": [5.0, 5.0],
        "errors": {},
        "gate_config_version": "gate",
    }
    if kind.startswith("null"):
        root = NullCalibration(
            **common,
            n_graduates=0,
            false_graduation_rate=0.0,
            max_deflated_sharpe=0.0,
            max_holdout_sharpe=None,
            graduates=[],
            walk_forward_oos_sharpes=[1e308, 1e308],
            purged_cv_oos_sharpes=[1e308, 1e308],
        )
        result = (
            root.walk_forward_null_percentiles
            if kind == "null-walk"
            else root.purged_cv_null_percentiles
        )
    else:
        power = PowerCalibration(
            **common,
            n_detected=0,
            detection_rate=0.0,
            oracle_sharpes=[1e308, 1e308],
            net_oracle_sharpes=[1e308, 1e308],
        )
        result = (
            power.oracle_sharpe_percentiles
            if kind == "power-gross"
            else power.net_oracle_sharpe_percentiles
        )
    assert result == (1e308, 1e308, 1e308)


@given(
    st.floats(min_value=MAX_FLOAT / 2, max_value=MAX_FLOAT, allow_nan=False, allow_infinity=False)
)
def test_large_equal_scores_preserve_point_mass(value: float) -> None:
    assert _percentiles([value, value]) == (value, value, value)


@given(
    st.floats(min_value=MAX_FLOAT / 2, max_value=MAX_FLOAT, allow_nan=False, allow_infinity=False)
)
def test_opposite_extreme_quantiles_stay_ordered_and_match_rational_oracle(value: float) -> None:
    values = [-value, value]
    result = _percentiles(values)
    assert result is not None
    middle, p95, maximum = result
    assert all(isfinite(v) for v in result)
    assert -value <= middle <= p95 <= maximum <= value
    assert result == (rational_quantile(values, 0.5), rational_quantile(values, 0.95), value)
