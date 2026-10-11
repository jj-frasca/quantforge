"""Finite original power evidence cannot publish invalid capture arithmetic."""

from math import copysign
from statistics import median
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab import calibration
from app.research.lab.calibration import PowerCalibration, collect_power_sweep
from app.research.lab.frontier import sharpe_standard_error

ACCESSORS = (
    "capture_ratio",
    "net_capture_ratio",
    "achievable_capture_ratio",
    "net_capture_by_category",
)


def cell(n: int = 2, **updates: Any) -> PowerCalibration:
    payload = {
        "n_symbols": n,
        "n_detected": 0,
        "detection_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 0.0,
        "oracle_sharpes": [1.0] * n,
        "net_oracle_sharpes": [1.0] * n,
        "achievable_oracle_sharpes": [1.0] * n,
        "finalist_observed_sharpes": [0.5] * n,
        "finalist_sharpes_by_category": {"Trend": [0.5] * n},
        "holdout_years": [5.0] * n,
        "n_bars": [7400] * n,
        "errors": {},
        "gate_config_version": "gate",
    }
    return PowerCalibration.model_validate(payload | updates)


@pytest.mark.parametrize("accessor", ACCESSORS)
@pytest.mark.parametrize("sign", [-1, 1])
def test_overflowing_finalist_median_cannot_publish_capture(accessor: str, sign: int) -> None:
    root = cell(finalist_observed_sharpes=[sign * 1e308] * 2)
    with pytest.raises(ValueError, match="capture"):
        getattr(root, accessor)


@pytest.mark.parametrize("accessor", ACCESSORS)
def test_overflowing_reference_median_is_not_zero_or_noise_refusal(accessor: str) -> None:
    root = cell(
        oracle_sharpes=[1e308] * 2,
        net_oracle_sharpes=[1e308] * 2,
        achievable_oracle_sharpes=[1e308] * 2,
    )
    with pytest.raises(ValueError, match="capture"):
        getattr(root, accessor)


@pytest.mark.parametrize("accessor", ACCESSORS[1:])
def test_native_noise_arithmetic_overflow_is_a_clear_capture_refusal(accessor: str) -> None:
    root = cell(net_oracle_sharpes=[1e200] * 2, achievable_oracle_sharpes=[1e200] * 2)
    with pytest.raises(ValueError, match="capture"):
        getattr(root, accessor)


@pytest.mark.parametrize("accessor", ACCESSORS[1:])
@pytest.mark.parametrize("n", [1, 2])
def test_unrepresentable_history_arithmetic_is_refused(accessor: str, n: int) -> None:
    root = cell(n, n_bars=[10**400] * n)
    with pytest.raises(ValueError, match="capture"):
        getattr(root, accessor)


@pytest.mark.parametrize("accessor", ACCESSORS)
def test_genuine_capture_quotient_overflow_is_refused(accessor: str) -> None:
    root = cell(
        1,
        oracle_sharpes=[0.5],
        net_oracle_sharpes=[0.5],
        achievable_oracle_sharpes=[0.5],
        finalist_observed_sharpes=[1e308],
        finalist_sharpes_by_category={"Trend": [1e308]},
    )
    assert sharpe_standard_error(0.5, 7400 / 252) < 0.5
    with pytest.raises(ValueError, match="capture"):
        getattr(root, accessor)


def test_category_only_median_overflow_cannot_publish_infinity() -> None:
    root = cell(finalist_sharpes_by_category={"Trend": [1e308] * 2})
    assert root.net_capture_ratio == 0.5
    with pytest.raises(ValueError, match="capture"):
        _ = root.net_capture_by_category


@pytest.mark.parametrize("boundary", ["json", "sweep"])
def test_computed_serialization_and_sweep_refuse_invalid_derived_capture(boundary: str) -> None:
    root = cell(finalist_observed_sharpes=[1e308] * 2)
    with pytest.raises(ValueError, match="capture"):
        if boundary == "json":
            root.model_dump_json()
        else:
            collect_power_sweep([root]).model_dump_json()


@pytest.mark.parametrize("accessor", ACCESSORS)
def test_partial_finalists_preserve_early_legacy_refusal(accessor: str) -> None:
    root = cell(finalist_observed_sharpes=[1e308], oracle_sharpes=[1e308] * 2)
    expected = {} if accessor == "net_capture_by_category" else None
    assert getattr(root, accessor) == expected


@pytest.mark.parametrize("reference", [-1.0, 0.0, 0.01])
def test_noise_refusal_does_not_evaluate_dormant_extreme_finalist(reference: float) -> None:
    root = cell(
        net_oracle_sharpes=[reference] * 2,
        achievable_oracle_sharpes=[reference] * 2,
        finalist_observed_sharpes=[1e308] * 2,
    )
    assert root.net_capture_ratio is None
    assert root.achievable_capture_ratio is None
    assert root.net_capture_by_category == {}


def test_nonpositive_gross_reference_preserves_early_refusal() -> None:
    assert (
        cell(oracle_sharpes=[-1.0] * 2, finalist_observed_sharpes=[1e308] * 2).capture_ratio is None
    )


def test_partial_category_remains_omitted_without_dormant_median_evaluation() -> None:
    root = cell(3, finalist_sharpes_by_category={"partial": [1e308] * 2, "full": [0.5] * 3})
    assert root.net_capture_by_category == {"full": 0.5}


def test_absent_history_preserves_net_and_achievable_legacy_refusal() -> None:
    root = cell(n_bars=[], finalist_observed_sharpes=[1e308] * 2)
    assert root.net_capture_ratio is None
    assert root.achievable_capture_ratio is None
    assert root.net_capture_by_category == {}


@pytest.mark.parametrize("accessor", ACCESSORS[1:])
def test_nonfinite_derived_noise_is_not_a_legitimate_refusal(
    accessor: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(calibration, "sharpe_standard_error", lambda *_: float("inf"))
    with pytest.raises(ValueError, match="capture"):
        getattr(cell(), accessor)


def test_noise_equality_retains_existing_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calibration, "sharpe_standard_error", lambda oracle, _: oracle)
    root = cell(finalist_observed_sharpes=[1e308] * 2)
    assert root.net_capture_ratio is None
    assert root.achievable_capture_ratio is None
    assert root.net_capture_by_category == {}


@pytest.mark.parametrize("value", [-0.0, -1e-320, -2.0, 3.0])
def test_signed_finite_capture_keeps_native_value_and_zero_sign(value: float) -> None:
    root = cell(
        1, finalist_observed_sharpes=[value], finalist_sharpes_by_category={"full": [value]}
    )
    for accessor in ACCESSORS:
        actual = getattr(root, accessor)
        if isinstance(actual, dict):
            actual = actual["full"]
        assert actual == value
        assert copysign(1.0, actual) == copysign(1.0, value)


def test_finite_quotient_underflow_retains_native_zero() -> None:
    root = cell(
        1,
        oracle_sharpes=[10.0],
        net_oracle_sharpes=[10.0],
        achievable_oracle_sharpes=[10.0],
        finalist_observed_sharpes=[5e-324],
        finalist_sharpes_by_category={"full": [5e-324]},
    )
    assert root.capture_ratio == 0.0
    assert root.net_capture_ratio == 0.0
    assert root.achievable_capture_ratio == 0.0
    assert root.net_capture_by_category == {"full": 0.0}


def test_noise_keeps_native_integer_history_division(monkeypatch: pytest.MonkeyPatch) -> None:
    bars = 9007199254740993
    years_seen: list[float] = []

    def noise(_: float, years: float) -> float:
        years_seen.append(years)
        return 0.0

    monkeypatch.setattr(calibration, "sharpe_standard_error", noise)
    root = cell(1, n_bars=[bars])
    assert root.net_capture_ratio == 0.5
    assert root.achievable_capture_ratio == 0.5
    assert root.net_capture_by_category == {"Trend": 0.5}
    assert years_seen == [bars / 252] * 3
    assert bars / 252 != float(bars) / 252


@pytest.mark.parametrize("accessor", ACCESSORS[1:])
def test_integer_median_beyond_float_range_keeps_finite_native_years(accessor: str) -> None:
    # Integer true division can produce finite years without first converting the integer.
    bars = 10**310
    assert bars / 252 < 1e308
    root = cell(1, n_bars=[bars])
    expected = {"Trend": 0.5} if accessor == "net_capture_by_category" else 0.5
    assert getattr(root, accessor) == expected


@given(
    st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False), min_size=1, max_size=8),
    st.floats(min_value=0.5, max_value=100, allow_nan=False),
    st.integers(min_value=252, max_value=100_000),
)
def test_finite_native_capture_and_noise_predicate_remain_exact(
    finalists: list[float], reference: float, bars: int
) -> None:
    n = len(finalists)
    root = cell(
        n,
        oracle_sharpes=[reference] * n,
        net_oracle_sharpes=[reference] * n,
        achievable_oracle_sharpes=[reference] * n,
        finalist_observed_sharpes=finalists,
        finalist_sharpes_by_category={"full": finalists},
        n_bars=[bars] * n,
    )
    oracle = median([reference] * n)
    ratio = median(finalists) / oracle
    permitted = oracle > sharpe_standard_error(oracle, median([bars] * n) / 252)
    assert root.capture_ratio == ratio
    assert root.net_capture_ratio == (ratio if permitted else None)
    assert root.achievable_capture_ratio == (ratio if permitted else None)
    assert root.net_capture_by_category == ({"full": ratio} if permitted else {})
