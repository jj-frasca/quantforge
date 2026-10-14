"""Exact represented sample Sharpe; subnormal recovery permits one output ULP."""

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
from app.research.lab.gate import GateConfig

_DTYPES = ["float64", "Float64"]
_V10 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10"
_V11 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-v11"
_V10_HASH = "ae63be276e14bc0edfd86c89667ca9f198af47273559a19e17ea7c4184252d7d"


def _exact_moments(returns: pd.Series) -> tuple[Fraction, Fraction]:
    values = [Fraction(*float(v).as_integer_ratio()) for v in returns]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, variance


def _oracle(returns: pd.Series, precision: int = 800) -> float:
    mean, variance = _exact_moments(returns)
    with localcontext() as context:
        context.prec = precision
        mu = Decimal(mean.numerator) / Decimal(mean.denominator)
        var = Decimal(variance.numerator) / Decimal(variance.denominator)
        return float(Decimal(252).sqrt() * mu / var.sqrt())


def _assert_subnormal_midpoints(returns: pd.Series, actual: float) -> None:
    # The correctly rounded score may be the adjacent representable output.
    # Compare exact squared scores to surrounding midpoint squares; no rounded sqrt oracle.
    mean, variance = _exact_moments(returns)
    squared = 252 * mean * mean / variance
    magnitude = abs(actual)
    previous = math.nextafter(magnitude, 0.0)
    previous_previous = math.nextafter(previous, 0.0)
    following = math.nextafter(magnitude, math.inf)
    following_following = math.nextafter(following, math.inf)
    lower = (Fraction(previous_previous) + Fraction(previous)) / 2
    upper = (Fraction(following) + Fraction(following_following)) / 2
    assert lower * lower <= squared <= upper * upper
    if actual != 0:
        assert math.copysign(1, actual) == math.copysign(1, float(mean))


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("n", [3, 4, 7])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_sharpe_original_tiny_nearconstant_dispersion(
    dtype: str, n: int, sign: int, mode: str
) -> None:
    base = 1e-200
    returns = pd.Series(sign * (base + np.arange(n) * math.ulp(base)), dtype=dtype, name="net")
    before = returns.copy(deep=True)
    expected = _oracle(returns)
    assert expected == _oracle(returns, 200)
    with np.errstate(all=mode):
        state = np.geterr()
        actual = metrics.sharpe_ratio(returns)
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=2e-15, abs=0)
    pd.testing.assert_series_equal(returns, before)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("scale", [1e-160, 1e-200, 1e-300])
@pytest.mark.parametrize("sign", [-1, 1])
def test_sharpe_mixed_signed_underflow_matches_centered_fraction(
    dtype: str, scale: float, sign: int
) -> None:
    returns = pd.Series(sign * np.array([-3, 1, 0, 2, 7]) * scale, dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics.sharpe_ratio(returns)
    assert actual == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("n", [3, 100])
@pytest.mark.parametrize("scale", [1.0, 1e-10, 1e150])
@pytest.mark.parametrize("sign", [-1, 1])
def test_sharpe_subnormal_and_zero_outputs_have_exact_midpoint_bound(
    dtype: str, n: int, scale: float, sign: int
) -> None:
    returns = pd.Series([-scale, sign * math.ulp(0.0), scale] + [0.0] * (n - 3), dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics.sharpe_ratio(returns)
    assert abs(actual) < np.finfo(float).tiny
    _assert_subnormal_midpoints(returns, actual)
    if scale == 1.0:
        expected = _oracle(returns)
        assert expected * sign > 0
        assert actual == expected


@settings(max_examples=80, deadline=None)
@example(dtype="Float64", exponent=-666, sign=1, offsets=[0, 1, 2])
@given(
    dtype=st.sampled_from(_DTYPES),
    exponent=st.integers(-1000, -600),
    sign=st.sampled_from([-1, 1]),
    offsets=st.lists(st.integers(0, 64), min_size=3, max_size=20),
)
def test_sharpe_nearconstant_ulps_property(
    dtype: str, exponent: int, sign: int, offsets: list[int]
) -> None:
    base = math.ldexp(1.0, exponent)
    returns = pd.Series(sign * (base + np.array(offsets) * math.ulp(base)), dtype=dtype)
    with np.errstate(all="raise"):
        result = metrics.sharpe_ratio(returns)
    if len(set(offsets)) == 1:
        assert result == 0
    else:
        assert result == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("values", [[], [0.1], [0.1] * 3, [0.0] * 3])
def test_sharpe_short_and_constant_guards_precede_recovery(values: list[float]) -> None:
    with patch.object(
        metrics,
        "_recover_float64_sharpe_dispersion",
        create=True,
        side_effect=AssertionError("guard must win"),
    ):
        assert metrics.sharpe_ratio(pd.Series(values, dtype="Float64")) == 0


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([True, False]),
        pd.Series([0.1, 0.2], dtype=object),
        pd.Series([1 + 0j, 2 + 0j]),
        pd.Series([np.nan]),
        pd.Series([np.inf]),
        pd.Series([pd.NA], dtype="Float64"),
    ],
)
def test_sharpe_source_validation_precedes_recovery(returns: pd.Series) -> None:
    with (
        patch.object(
            metrics,
            "_recover_float64_sharpe_dispersion",
            create=True,
            side_effect=AssertionError("source guard must win"),
        ),
        pytest.raises(ValueError),
    ):
        metrics.sharpe_ratio(returns)


@pytest.mark.parametrize(
    "dtype", ["float16", "float32", "Float32", "int64", "Int64", np.longdouble]
)
def test_sharpe_other_source_families_bypass_recovery(dtype: str | type) -> None:
    returns = pd.Series([0, 1, 3, 2], dtype=dtype)
    expected = float(np.sqrt(252) * float(returns.mean()) / float(returns.std()))
    with patch.object(
        metrics,
        "_recover_float64_sharpe_dispersion",
        create=True,
        side_effect=AssertionError("outside source family"),
    ):
        assert metrics.sharpe_ratio(returns) == expected


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sharpe_measurable_native_score_bypasses_recovery(dtype: str) -> None:
    returns = pd.Series([-0.01, 0.02, -0.03, 0.04, 0.01], dtype=dtype)
    expected = float(np.sqrt(252) * float(returns.mean()) / float(returns.std()))
    with patch.object(
        metrics,
        "_recover_float64_sharpe_dispersion",
        create=True,
        side_effect=AssertionError("native score must remain"),
    ):
        assert metrics.sharpe_ratio(returns) == expected


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sharpe_nonfinite_native_std_keeps_original_scale_recovery(dtype: str) -> None:
    returns = pd.Series([-1e200, 2e200, 3e200], dtype=dtype)
    with np.errstate(all="ignore"):
        assert not np.isfinite(returns.std())
    with patch.object(
        metrics,
        "_recover_float64_sharpe_dispersion",
        create=True,
        side_effect=AssertionError("nonfinite STD remains separate"),
    ):
        assert metrics.sharpe_ratio(returns) == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("failure", ["mean", "ratio"])
def test_sharpe_only_std_failure_selects_anchored_recovery(failure: str) -> None:
    returns = pd.Series([0.0, 1.0, 2.0])
    # Inject failure after a successful native STD, preserving provenance of the recovery trigger.
    stds = [1.0, 0.5] if failure == "mean" else [1e-10, 0.5]
    mean = FloatingPointError("mean underflow") if failure == "mean" else math.ulp(0.0)
    with (
        patch.object(pd.Series, "std", side_effect=stds),
        patch.object(
            pd.Series,
            "mean",
            side_effect=mean if isinstance(mean, Exception) else None,
            return_value=mean,
        ),
        patch.object(
            metrics,
            "_recover_float64_sharpe_dispersion",
            create=True,
            side_effect=AssertionError("STD did not fail"),
        ),
    ):
        assert math.isfinite(metrics.sharpe_ratio(returns))


def test_sharpe_anchored_correction_invalidates_frozen_v10_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert calibration._TRIAL_ACCOUNTING_VERSION == _V11
    kwargs = {
        "n_per_param": 3,
        "config": GateConfig(),
        "refine": True,
        "refine_span": 0.25,
    }
    current = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert current != _V10_HASH
    monkeypatch.setattr(calibration, "_TRIAL_ACCOUNTING_VERSION", _V10)
    assert calibration.calibration_search_version(["sma", "momentum"], **kwargs) == _V10_HASH


@pytest.mark.parametrize("dtype", ["float16", "float32", "Float32", np.longdouble])
def test_sharpe_other_dtype_native_underflow_uses_prior_recovery(
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
        "_recover_float64_sharpe_dispersion",
        create=True,
        side_effect=AssertionError("other dtype must retain recovery"),
    ):
        actual = metrics.sharpe_ratio(returns)
    assert actual == pytest.approx(_oracle(returns), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
def test_sharpe_finite_native_std_collapse_selects_anchored_recovery(
    dtype: str,
) -> None:
    returns = pd.Series([0.0, 1.0, 2.0], dtype=dtype)
    with (
        patch.object(pd.Series, "std", side_effect=[0.0, 0.5]),
        patch.object(
            metrics,
            "_recover_float64_sharpe_dispersion",
            wraps=metrics._recover_float64_sharpe_dispersion,
        ) as helper,
    ):
        result = metrics.sharpe_ratio(returns)
    assert helper.call_count == 1
    assert result == float(np.sqrt(252))
