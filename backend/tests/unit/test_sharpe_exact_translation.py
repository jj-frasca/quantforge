"""Exact-translation Sharpe scope; native numerator, exact represented variance."""

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

_V12 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-v12"
_V13 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13"
_V14 = _V13.removesuffix("-v13") + "-oos-exact-translation-v14"


def test_sharpe_translation_advances_identity_and_preserves_historical_v12(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert calibration._TRIAL_ACCOUNTING_VERSION == _V14
    kwargs = {"n_per_param": 3, "config": GateConfig(), "refine": True, "refine_span": 0.25}
    current = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert current == "ece94d5f4a3d9713249f42ab7764128b348415487bdc411b608c2dc93f930080"
    monkeypatch.setattr(calibration, "_TRIAL_ACCOUNTING_VERSION", _V12)
    historical = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert historical == "d84be10e9f71134607ce9c42db52eedee71cc93f2f45db8b0acf637ab592bf68"
    assert current != historical


_DTYPES = ["float64", "Float64"]
_HELPER = "_sharpe_from_exact_float64_translation"


def _oracle(returns: pd.Series, mean: float, precision: int = 800) -> float:
    values = [Fraction(float(v)) for v in returns]
    exact_mean = sum(values) / len(values)
    variance = sum((v - exact_mean) ** 2 for v in values) / (len(values) - 1)
    # Numerator is intentionally the already accepted native mean, not exact sample mean.
    numerator = Fraction(mean)
    with localcontext() as c:
        c.prec = precision
        return float(
            Decimal(252).sqrt()
            * (Decimal(numerator.numerator) / Decimal(numerator.denominator))
            / (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        )


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("base,n", [(1e-100, 3), (0.01, 4), (1.0, 7), (0.1, 4)])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_native_positive_std_preserves_represented_dispersion(
    dtype: str | type, base: float, n: int, sign: int, mode: str
) -> None:
    returns = pd.Series(sign * (base + np.arange(n) * math.ulp(base)), dtype=dtype)
    before = returns.copy(deep=True)
    with np.errstate(all="raise"):
        assert returns.std() > 0
        mean = float(returns.mean())
    expected = _oracle(returns, mean)
    assert expected == _oracle(returns, mean, 200)
    with np.errstate(all=mode):
        state = np.geterr()
        actual = metrics.sharpe_ratio(returns)
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=5e-14, abs=0)
    pd.testing.assert_series_equal(returns, before)


@settings(max_examples=60, deadline=None)
@example(dtype="Float64", exponent=-333, sign=1, offsets=[0, 1, 2])
@given(
    dtype=st.sampled_from(_DTYPES),
    exponent=st.integers(-450, 490),
    sign=st.sampled_from([-1, 1]),
    offsets=st.lists(st.integers(0, 64), min_size=2, max_size=30),
)
def test_exact_translation_binary_grid_property(
    dtype: str | type, exponent: int, sign: int, offsets: list[int]
) -> None:
    base = math.ldexp(1.0, exponent)
    returns = pd.Series(sign * (base + np.array(offsets) * math.ulp(base)), dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics.sharpe_ratio(returns)
        mean = float(returns.mean())
    if len(set(offsets)) == 1:
        assert actual == 0
    else:
        assert actual == pytest.approx(_oracle(returns, mean), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("values", [[1.0, 1.125, 1.75], [1.0, 2.0], [1.0, math.nextafter(2.0, 0)]])
def test_same_sign_ordinary_and_boundary_variance(
    dtype: str | type, sign: int, values: list[float]
) -> None:
    returns = pd.Series(sign * np.array(values), dtype=dtype)
    with np.errstate(all="raise"):
        actual = metrics.sharpe_ratio(returns)
    assert actual == pytest.approx(_oracle(returns, float(returns.mean())), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("sign", [-1, 1])
def test_two_min_boundary_selects_and_passes_actual_native_mean(
    dtype: str | type, sign: int
) -> None:
    returns = pd.Series(sign * np.array([1.0, 2.0]), dtype=dtype)
    mean = float(returns.mean())
    with patch.object(metrics, _HELPER, create=True, return_value=17.0) as helper:
        assert metrics.sharpe_ratio(returns) == 17.0
    helper.assert_called_once()
    args = helper.call_args.args
    np.testing.assert_array_equal(args[0], returns.to_numpy(dtype=np.float64))
    assert args[1] == mean


@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize(
    "values",
    [
        [1.0, math.nextafter(2.0, math.inf)],
        [-1.0, -math.nextafter(2.0, math.inf)],
        [0.0, 1.0, 2.0],
        [-1.0, 1.0, 2.0],
        [1.0, 2.0, 4.0],
    ],
)
def test_wide_zero_mixed_source_keeps_native_exact(dtype: str | type, values: list[float]) -> None:
    returns = pd.Series(values, dtype=dtype)
    expected = float(np.sqrt(252) * float(returns.mean()) / float(returns.std()))
    with patch.object(
        metrics,
        _HELPER,
        create=True,
        side_effect=AssertionError("outside exact-translation region"),
    ):
        assert metrics.sharpe_ratio(returns) == expected


@pytest.mark.parametrize(
    "dtype", ["float16", "float32", "Float32", "int64", "Int64", np.longdouble]
)
def test_other_original_sources_keep_native_exact(dtype: str | type) -> None:
    returns = pd.Series(
        [1, 1.25, 1.5] if dtype not in ["int64", "Int64"] else [2, 3, 4], dtype=dtype
    )
    expected = float(np.sqrt(252) * float(returns.mean()) / float(returns.std()))
    with patch.object(
        metrics,
        _HELPER,
        create=True,
        side_effect=AssertionError("outside original Float64"),
    ):
        assert metrics.sharpe_ratio(returns) == expected


@pytest.mark.parametrize("values", [[], [1.0], [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]])
def test_short_constant_precedes_translation(values: list[float]) -> None:
    with patch.object(metrics, _HELPER, create=True, side_effect=AssertionError("guard")):
        assert metrics.sharpe_ratio(pd.Series(values, dtype="Float64")) == 0


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([True]),
        pd.Series([1], dtype=object),
        pd.Series([1j]),
        pd.Series([np.inf]),
        pd.Series([np.nan]),
        pd.Series([pd.NA], dtype="Float64"),
    ],
)
def test_original_source_guard_precedes_translation(returns: pd.Series) -> None:
    with (
        patch.object(metrics, _HELPER, create=True, side_effect=AssertionError("guard")),
        pytest.raises(ValueError),
    ):
        metrics.sharpe_ratio(returns)


@pytest.mark.parametrize("dtype", _DTYPES)
def test_real_underflow_keeps_existing_anchored_recovery(dtype: str | type) -> None:
    base = 1e-200
    returns = pd.Series(base + np.arange(3) * math.ulp(base), dtype=dtype)
    expected = _oracle(returns, float(returns.mean()))
    with patch.object(
        metrics,
        _HELPER,
        create=True,
        side_effect=AssertionError("STD underflow remains ADR286"),
    ):
        assert metrics.sharpe_ratio(returns) == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("stds", [[FloatingPointError(), 0.25, 0.5], [0.0, 0.5], [math.inf, 0.5]])
def test_std_failure_provenance_keeps_prior_recovery(
    stds: list[float | FloatingPointError],
) -> None:
    with (
        patch.object(pd.Series, "std", side_effect=stds),
        patch.object(
            metrics,
            _HELPER,
            create=True,
            side_effect=AssertionError("failed/nonfinite native STD"),
        ),
    ):
        assert math.isfinite(metrics.sharpe_ratio(pd.Series([1.0, 1.25, 1.5])))


def test_mean_only_underflow_keeps_prior_recovery() -> None:
    with (
        patch.object(pd.Series, "mean", side_effect=FloatingPointError()),
        patch.object(
            metrics,
            _HELPER,
            create=True,
            side_effect=AssertionError("native mean failed"),
        ),
    ):
        assert math.isfinite(metrics.sharpe_ratio(pd.Series([1.0, 1.25, 1.5])))


def test_native_zero_mean_keeps_prior_sum_evidence_path() -> None:
    with (
        patch.object(pd.Series, "mean", return_value=0.0),
        patch.object(
            metrics,
            _HELPER,
            create=True,
            side_effect=AssertionError("zero native mean"),
        ),
    ):
        assert math.isfinite(metrics.sharpe_ratio(pd.Series([1.0, 1.25, 1.5])))


def test_ratio_only_underflow_keeps_prior_recovery() -> None:
    original = np.sqrt
    raised = False

    def underflow_once(value: object, *args: object, **kwargs: object) -> object:
        nonlocal raised
        if np.isscalar(value) and value == 252 and not raised:
            raised = True
            raise FloatingPointError("injected ratio underflow")
        return original(value, *args, **kwargs)

    with (
        patch.object(np, "sqrt", side_effect=underflow_once),
        patch.object(
            metrics,
            _HELPER,
            create=True,
            side_effect=AssertionError("native ratio failed"),
        ),
    ):
        assert math.isfinite(metrics.sharpe_ratio(pd.Series([1.0, 1.25, 1.5])))
    assert raised


def test_accepted_native_mean_is_not_replaced_by_fsum() -> None:
    returns = pd.Series([1.0, 1.25, 1.5])
    with (
        patch.object(metrics, "fsum", side_effect=AssertionError("native nonzero mean remains")),
        patch.object(metrics, _HELPER, create=True, return_value=17.0) as helper,
    ):
        assert metrics.sharpe_ratio(returns) == 17.0
    assert helper.call_args.args[1] == float(returns.mean())


def test_corrected_score_propagates_into_iid_interval() -> None:
    base = 1e-100
    returns = pd.Series(base + np.arange(252) * math.ulp(base))
    score = _oracle(returns, float(returns.mean()))
    width = 1.959963984540054 * math.sqrt(1 + score**2 / (2 * 252))
    interval = metrics.sharpe_confidence_interval(returns)
    assert interval is not None
    assert interval.lower == pytest.approx(score - width, rel=5e-14, abs=0)
    assert interval.upper == pytest.approx(score + width, rel=5e-14, abs=0)


@pytest.mark.parametrize(
    "base,n,expected",
    [
        (
            0.01,
            4,
            {
                "max_drawdown": 0.0,
                "total_return": 0.040604010000000024,
                "annualized_return": 11.274002099240223,
                "annualized_vol": 3.8944445447392736e-17,
                "sortino": 0.0,
                "calmar": 0.0,
                "sharpe_ci": None,
            },
        ),
        (
            1e-100,
            3,
            {
                "max_drawdown": 0.0,
                "total_return": 0.0,
                "annualized_return": 0.0,
                "annualized_vol": 3.1850917274256776e-115,
                "sortino": 0.0,
                "calmar": 0.0,
                "sharpe_ci": None,
            },
        ),
        (
            0.1,
            7,
            {
                "max_drawdown": 0.0,
                "total_return": 0.9487171000000005,
                "annualized_return": 26974702266.758247,
                "annualized_vol": 4.759089844286815e-16,
                "sortino": 0.0,
                "calmar": 0.0,
                "sharpe_ci": None,
            },
        ),
    ],
)
def test_public_other_fields_retain_literal_original_snapshots(
    base: float, n: int, expected: dict[str, float | None]
) -> None:
    returns = pd.Series(base + np.arange(n) * math.ulp(base))
    actual = metrics.BacktestMetrics.from_series(returns)
    for field, value in expected.items():
        assert getattr(actual, field) == value
