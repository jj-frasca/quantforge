"""Anchored volatility controls; one output ULP permitted on subnormal fixtures."""

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.backtesting import metrics
from app.research.lab import calibration

_DTYPES = ["float64", "Float64"]


def _variance(returns: pd.Series) -> Fraction:
    x = [Fraction(*float(v).as_integer_ratio()) for v in returns]
    mean = sum(x) / len(x)
    return sum((v - mean) ** 2 for v in x) / (len(x) - 1)


def _oracle(returns: pd.Series, precision: int = 800) -> float:
    variance = _variance(returns)
    with localcontext() as context:
        context.prec = precision
        return float((252 * Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt())


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("n", [3, 4, 7])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_volatility_original_nearconstant_dispersion(
    dtype: str, n: int, sign: int, mode: str
) -> None:
    b = 1e-200
    returns = pd.Series(sign * (b + np.arange(n) * math.ulp(b)), dtype=dtype)
    before = returns.copy(deep=True)
    expected = _oracle(returns)
    assert expected == _oracle(returns, 200)
    with np.errstate(all=mode):
        state = np.geterr()
        actual = metrics.BacktestMetrics.from_series(returns).annualized_vol
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=2e-15, abs=0)
    pd.testing.assert_series_equal(returns, before)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize(
    "values",
    [
        [0, 1],
        [-1, 1],
        [0, 1, 2],
        [0, 1, 0, 0, 0, 0, 0],
        [-1, 1, 0, 0, 0, 0, 0],
        [0, 1, 2] + [0] * 97,
    ],
)
def test_volatility_subnormal_exact_squared_midpoint_controls(
    dtype: str, values: list[int]
) -> None:
    returns = pd.Series(np.array(values) * math.ulp(0.0), dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics._annualized_volatility(returns)
    squared = 252 * _variance(returns)
    previous = math.nextafter(actual, 0.0)
    previous_previous = math.nextafter(previous, 0.0)
    following = math.nextafter(actual, math.inf)
    following_following = math.nextafter(following, math.inf)
    lower = (Fraction(previous_previous) + Fraction(previous)) / 2
    upper = (Fraction(following) + Fraction(following_following)) / 2
    assert lower * lower <= squared <= upper * upper
    assert actual > 0
    if values == [0, 1]:
        assert actual == _oracle(returns)


@settings(max_examples=60, deadline=None)
@example(dtype="Float64", exponent=-666, sign=-1, offsets=[0, 1, 2])
@given(
    dtype=st.sampled_from(_DTYPES),
    exponent=st.integers(-1000, -600),
    sign=st.sampled_from([-1, 1]),
    offsets=st.lists(st.integers(0, 64), min_size=3, max_size=20),
)
def test_volatility_original_ulp_property(
    dtype: str, exponent: int, sign: int, offsets: list[int]
) -> None:
    b = math.ldexp(1.0, exponent)
    returns = pd.Series(sign * (b + np.array(offsets) * math.ulp(b)), dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics._annualized_volatility(returns)
    if len(set(offsets)) == 1:
        assert actual == 0
    else:
        assert actual == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("values", [[], [0.1], [0.1] * 3, [0.0] * 3])
def test_volatility_short_constant_guards_precede_recovery(values: list[float]) -> None:
    with patch.object(
        metrics,
        "_recover_float64_volatility_dispersion",
        create=True,
        side_effect=AssertionError("guard must win"),
    ):
        assert metrics._annualized_volatility(pd.Series(values, dtype="Float64")) == 0


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([True]),
        pd.Series([0.1], dtype=object),
        pd.Series([1 + 0j]),
        pd.Series([np.nan]),
        pd.Series([np.inf]),
        pd.Series([pd.NA], dtype="Float64"),
    ],
)
def test_volatility_source_guards_precede_recovery(returns: pd.Series) -> None:
    with (
        patch.object(
            metrics,
            "_recover_float64_volatility_dispersion",
            create=True,
            side_effect=AssertionError("source guard must win"),
        ),
        pytest.raises(ValueError),
    ):
        metrics._annualized_volatility(returns)


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
def test_volatility_native_measurable_results_remain_exact(dtype: str | type) -> None:
    returns = pd.Series([0, 1, 3, 2], dtype=dtype)
    expected = float(returns.std() * np.sqrt(252))
    with patch.object(
        metrics,
        "_recover_float64_volatility_dispersion",
        create=True,
        side_effect=AssertionError("native estimator must remain"),
    ):
        assert metrics._annualized_volatility(returns) == expected


@pytest.mark.parametrize("dtype", ["float16", "float32", "Float32", np.longdouble])
def test_volatility_other_dtype_underflow_retains_prior_recovery(
    dtype: str | type,
) -> None:
    scale = (
        float(np.finfo(np.float16).smallest_subnormal)
        if dtype == "float16"
        else 1e-23
        if dtype in {"float32", "Float32"}
        else 1e-200
    )
    returns = pd.Series(np.array([-3, 1, 2, 7]) * scale, dtype=dtype)
    with patch.object(
        metrics,
        "_recover_float64_volatility_dispersion",
        create=True,
        side_effect=AssertionError("outside source family"),
    ):
        assert metrics._annualized_volatility(returns) == pytest.approx(
            _oracle(returns), rel=5e-14, abs=0
        )


@pytest.mark.parametrize("dtype", _DTYPES)
def test_volatility_nonfinite_native_std_retains_prior_recovery(dtype: str) -> None:
    returns = pd.Series([-1e200, 2e200, 3e200], dtype=dtype)
    with patch.object(
        metrics,
        "_recover_float64_volatility_dispersion",
        create=True,
        side_effect=AssertionError("nonfinite native STD stays separate"),
    ):
        assert metrics._annualized_volatility(returns) == pytest.approx(
            _oracle(returns), rel=5e-14, abs=0
        )


@pytest.mark.parametrize("dtype", _DTYPES)
def test_volatility_final_zero_preserves_existing_positive_measurement_contract(
    dtype: str,
) -> None:
    returns = pd.Series([math.ulp(0.0)] + [0.0] * 9999, dtype=dtype)
    assert _oracle(returns) == 0
    with pytest.raises(ValueError, match="volatility"):
        metrics._annualized_volatility(returns)


def test_volatility_true_upper_overflow_refuses() -> None:
    returns = pd.Series([-np.finfo(float).max, np.finfo(float).max])
    with np.errstate(all="raise"), pytest.raises(ValueError, match="volatility"):
        metrics._annualized_volatility(returns)


def test_volatility_annualization_only_underflow_does_not_select_anchored_std() -> None:
    returns = pd.Series([0.0, 1.0, 2.0])
    with (
        patch.object(pd.Series, "std", side_effect=[1e-320, 0.5]),
        patch.object(
            metrics,
            "_recover_float64_volatility_dispersion",
            create=True,
            side_effect=AssertionError("native STD succeeded"),
        ),
    ):
        assert metrics._annualized_volatility(returns) == float(np.sqrt(252))


def test_volatility_finite_std_collapse_selects_anchored_recovery() -> None:
    with (
        patch.object(pd.Series, "std", side_effect=[0.0, 0.5]),
        patch.object(
            metrics,
            "_recover_float64_volatility_dispersion",
            wraps=metrics._recover_float64_volatility_dispersion,
        ) as helper,
    ):
        assert metrics._annualized_volatility(pd.Series([0.0, 1.0, 2.0])) == float(np.sqrt(252))
    assert helper.call_count == 1


@pytest.mark.parametrize("dtype", _DTYPES)
def test_volatility_std_underflow_finite_recomputation_selects_anchored(
    dtype: str,
) -> None:
    with (
        patch.object(pd.Series, "std", side_effect=[FloatingPointError(), 0.25]),
        patch.object(
            metrics,
            "_recover_float64_volatility_dispersion",
            create=True,
            return_value=2.0,
        ) as helper,
    ):
        assert metrics._annualized_volatility(pd.Series([0.0, 1.0, 2.0], dtype=dtype)) == 2.0
    assert helper.call_count == 1


@pytest.mark.parametrize("dtype", _DTYPES)
def test_volatility_std_underflow_nonfinite_recomputation_keeps_prior_recovery(
    dtype: str,
) -> None:
    with (
        patch.object(pd.Series, "std", side_effect=[FloatingPointError(), math.inf, 0.5]),
        patch.object(
            metrics,
            "_recover_float64_volatility_dispersion",
            create=True,
            side_effect=AssertionError("nonfinite STD stays separate"),
        ),
    ):
        assert metrics._annualized_volatility(pd.Series([0.0, 1.0, 2.0], dtype=dtype)) == float(
            np.sqrt(252)
        )


def test_descriptive_volatility_keeps_current_v13_accounting() -> None:
    assert (
        calibration._TRIAL_ACCOUNTING_VERSION
        == "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13"
    )
