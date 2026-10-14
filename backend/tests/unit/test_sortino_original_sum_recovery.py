"""Original-sum Sortino recovery; selected exact and subnormal midpoint controls."""

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import permutations
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.backtesting import metrics
from app.research.lab import calibration

_DTYPES = ["float64", "Float64"]


def _moments(values: pd.Series) -> tuple[Fraction, Fraction]:
    observations = [Fraction(float(v)) for v in values]
    return sum(observations), sum(min(v, 0) ** 2 for v in observations) / len(values)


def _oracle(values: pd.Series, precision: int = 800) -> float:
    total, squared = _moments(values)
    with localcontext() as context:
        context.prec = precision
        numerator = Decimal(total.numerator) / Decimal(total.denominator)
        downside = (Decimal(squared.numerator) / Decimal(squared.denominator)).sqrt()
        return float(Decimal(252).sqrt() * numerator / len(values) / downside)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("bump", [-1, 0, 1, 2])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_sortino_original_cancellation_sum_recovers(
    dtype: str, bump: int, sign: int, mode: str
) -> None:
    returns = pd.Series(
        sign * np.array([-3e-200, 1e-200, 2e-200 + bump * math.ulp(2e-200)]),
        dtype=dtype,
    )
    before = returns.copy(deep=True)
    expected = _oracle(returns)
    assert expected == _oracle(returns, 200)
    with np.errstate(all=mode):
        state = np.geterr()
        actual = metrics.sortino_ratio(returns)
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=3e-15, abs=0)
    pd.testing.assert_series_equal(returns, before)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_sortino_original_zero_survives_observation_order(
    dtype: str, order: tuple[int, ...]
) -> None:
    values = [-3e-200, 1e-200, 2e-200]
    with np.errstate(all="raise"):
        assert metrics.sortino_ratio(pd.Series([values[i] for i in order], dtype=dtype)) == 0


@settings(max_examples=60, deadline=None)
@example(dtype="Float64", exponent=-666, a=3, bump=1, nzero=97)
@given(
    dtype=st.sampled_from(_DTYPES),
    exponent=st.integers(-1000, -550),
    a=st.sampled_from([3, 5, 7]),
    bump=st.integers(-8, 8),
    nzero=st.integers(0, 100),
)
def test_sortino_original_sum_property(
    dtype: str, exponent: int, a: int, bump: int, nzero: int
) -> None:
    b = math.ldexp(1.0, exponent)
    returns = pd.Series(
        [-a * b, b, (a - 1) * b + bump * math.ulp((a - 1) * b)] + [0.0] * nzero,
        dtype=dtype,
    )
    with np.errstate(all="raise"):
        actual = metrics.sortino_ratio(returns)
    assert actual == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("nzero", [0, 3, 97])
@pytest.mark.parametrize("sign", [-1, 1])
def test_sortino_partial_underflow_subnormal_squared_midpoints(
    dtype: str, nzero: int, sign: int
) -> None:
    tiny = math.ulp(0.0)
    returns = pd.Series([-1.0, -tiny, 2 * tiny, 1.0] + [0.0] * nzero, dtype=dtype)
    if sign < 0:
        returns = -returns
    with np.errstate(all="raise"):
        actual = metrics.sortino_ratio(returns)
    assert actual is not None
    assert actual != 0
    total, downside = _moments(returns)
    squared = 252 * total**2 / len(returns) ** 2 / downside
    magnitude = abs(actual)
    previous = math.nextafter(magnitude, 0.0)
    previous_previous = math.nextafter(previous, 0.0)
    following = math.nextafter(magnitude, math.inf)
    following_following = math.nextafter(following, math.inf)
    lower = (Fraction(previous_previous) + Fraction(previous)) / 2
    upper = (Fraction(following) + Fraction(following_following)) / 2
    assert lower**2 <= squared <= upper**2
    assert math.copysign(1, actual) == math.copysign(1, sign)


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sortino_downside_underflow_finite_recomputation_selects_original_sum(
    dtype: str,
) -> None:
    with (
        patch.object(np, "mean", side_effect=[FloatingPointError(), 0.25]),
        patch.object(
            metrics, "_recover_float64_sortino_downside", create=True, return_value=2.0
        ) as helper,
    ):
        assert metrics.sortino_ratio(pd.Series([-1.0, 2.0, 3.0], dtype=dtype)) == 2.0
    assert helper.call_count == 1


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sortino_downside_nonfinite_recomputation_keeps_prior_path(dtype: str) -> None:
    with (
        patch.object(np, "mean", side_effect=[FloatingPointError(), math.inf, 0.25]),
        patch.object(
            metrics,
            "_recover_float64_sortino_downside",
            create=True,
            side_effect=AssertionError("nonfinite downside"),
        ),
    ):
        expected = float(np.sqrt(252) * 4 / 3 / 0.5)
        assert metrics.sortino_ratio(pd.Series([-1.0, 2.0, 3.0], dtype=dtype)) == expected


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sortino_finite_downside_collapse_selects_original_sum(dtype: str) -> None:
    with (
        patch.object(np, "mean", return_value=0.0),
        patch.object(
            metrics, "_recover_float64_sortino_downside", create=True, return_value=2.0
        ) as helper,
    ):
        assert metrics.sortino_ratio(pd.Series([-1.0, 2.0, 3.0], dtype=dtype)) == 2.0
    assert helper.call_count == 1


@pytest.mark.parametrize(
    "dtype", ["float16", "float32", "Float32", "int64", "Int64", np.longdouble]
)
def test_sortino_other_source_families_keep_prior_recovery(dtype: str | type) -> None:
    values = [-3, 1, 2]
    with (
        patch.object(np, "mean", side_effect=[FloatingPointError(), 1 / 3]),
        patch.object(
            metrics,
            "_recover_float64_sortino_downside",
            create=True,
            side_effect=AssertionError("outside family"),
        ),
    ):
        metrics.sortino_ratio(pd.Series(values, dtype=dtype))


def test_sortino_nonzero_target_keeps_prior_recovery() -> None:
    with patch.object(
        metrics,
        "_recover_float64_sortino_downside",
        create=True,
        side_effect=AssertionError("nonzero target"),
    ):
        assert metrics.sortino_ratio(pd.Series([0.0, 1.0]), target=1e-160) is not None


def test_sortino_mean_only_underflow_keeps_prior_recovery() -> None:
    with (
        patch.object(pd.Series, "mean", side_effect=FloatingPointError()),
        patch.object(
            metrics,
            "_recover_float64_sortino_downside",
            create=True,
            side_effect=AssertionError("native downside succeeded"),
        ),
    ):
        assert metrics.sortino_ratio(pd.Series([-1.0, 2.0, 3.0])) is not None


@pytest.mark.parametrize("values", [[], [0.1], [0.1, 0.2]])
def test_sortino_short_no_downside_precedes_recovery(values: list[float]) -> None:
    with patch.object(
        metrics,
        "_recover_float64_sortino_downside",
        create=True,
        side_effect=AssertionError("guard"),
    ):
        assert metrics.sortino_ratio(pd.Series(values, dtype="Float64")) == 0


@pytest.mark.parametrize("values", [[np.nan], [np.inf], [True], ["0.1"], [1j]])
def test_sortino_source_guards_precede_recovery(values: list) -> None:
    with (
        patch.object(
            metrics,
            "_recover_float64_sortino_downside",
            create=True,
            side_effect=AssertionError("guard"),
        ),
        pytest.raises(ValueError),
    ):
        metrics.sortino_ratio(pd.Series(values))


def test_sortino_original_sum_overflow_keeps_prior_fallback() -> None:
    returns = pd.Series([-1e-200, 1e308, 1e308])
    with patch.object(
        metrics,
        "_recover_float64_sortino_downside",
        create=True,
        side_effect=AssertionError("uncertified sum"),
    ):
        assert metrics.sortino_ratio(returns) is None


def test_sortino_true_upper_overflow_remains_unmeasured() -> None:
    with np.errstate(all="raise"):
        assert metrics.sortino_ratio(pd.Series([-math.ulp(0.0), 1.0])) is None


def test_sortino_descriptive_correction_keeps_v11() -> None:
    assert calibration._TRIAL_ACCOUNTING_VERSION.endswith("verified-zero-anchored-dispersion-v11")


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("nzero", [0, 9997])
def test_sortino_negative_partial_underflow_legitimate_final_zero(dtype: str, nzero: int) -> None:
    returns = pd.Series([-1.0, 1.0, -math.ulp(0.0)] + [0.0] * nzero, dtype=dtype)
    total, downside = _moments(returns)
    squared_units = 252 * total**2 / len(returns) ** 2 / downside / Fraction(math.ulp(0.0)) ** 2
    nearest = math.isqrt(squared_units.numerator // squared_units.denominator)
    halfway = Fraction(2 * nearest + 1, 2) ** 2
    if squared_units > halfway or (squared_units == halfway and nearest % 2):
        nearest += 1
    expected = -math.ldexp(float(nearest), -1074)
    with np.errstate(all="raise"):
        actual = metrics.sortino_ratio(returns)
    assert actual is not None
    assert abs(Fraction(actual) - Fraction(expected)) <= Fraction(math.ulp(0.0))
    assert math.copysign(1, actual) == -1
    if nzero:
        assert expected == 0 and actual == 0


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sortino_near_max_recovery_remains_finite(dtype: str) -> None:
    returns = pd.Series([-1e-308, 0.1], dtype=dtype)
    expected = _oracle(returns)
    assert math.isfinite(expected)
    with np.errstate(all="raise"):
        actual = metrics.sortino_ratio(returns)
    assert actual == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sortino_multiple_shortfalls_preserve_original_total(dtype: str) -> None:
    b = 1e-200
    returns = pd.Series([-5 * b, -2 * b, 3 * b, 4 * b + math.ulp(4 * b)], dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics.sortino_ratio(returns)
    assert actual == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize(
    "dtype",
    [
        "float16",
        "float32",
        "Float32",
        "float64",
        "Float64",
        "int64",
        "Int64",
        np.longdouble,
    ],
)
def test_sortino_native_ordinary_result_remains_exact(dtype: str | type) -> None:
    returns = pd.Series([-1, 2, 3, 4], dtype=dtype)
    downside = np.minimum(returns.to_numpy(dtype=np.float64), 0.0)
    expected = float(np.sqrt(252) * float(returns.mean()) / float(np.sqrt(np.mean(downside**2))))
    with patch.object(
        metrics,
        "_recover_float64_sortino_downside",
        create=True,
        side_effect=AssertionError("native succeeded"),
    ):
        assert metrics.sortino_ratio(returns) == expected


def test_sortino_ratio_only_underflow_keeps_prior_recovery() -> None:
    with (
        patch.object(
            np,
            "sqrt",
            side_effect=[1.0, FloatingPointError(), math.sqrt(1 / 3), math.sqrt(252)],
        ),
        patch.object(
            metrics,
            "_recover_float64_sortino_downside",
            create=True,
            side_effect=AssertionError("downside succeeded"),
        ),
    ):
        assert metrics.sortino_ratio(pd.Series([-1.0, 2.0, 3.0])) is not None
