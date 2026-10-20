"""ADR-329: zero native dispersion requires identical converted observations."""

import math
import warnings
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.parameter_stability import parameter_stability


def exact_sample_std(values: list[float]) -> Decimal:
    exact = [Fraction.from_float(value) for value in values]
    center = sum(exact) / len(exact)
    variance = sum((value - center) ** 2 for value in exact) / (len(exact) - 1)
    assert variance > 0
    with localcontext() as context:
        context.prec = 100
        return (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()


@pytest.mark.parametrize("values", [[1e-200, 2e-200], [0.0, 1e-200], [-1e-200, 1e-200]])
@pytest.mark.parametrize("policy", ["ignore", "warn"])
def test_representable_positive_exact_dispersion_cannot_publish_zero(
    values: list[float],
    policy: str,
) -> None:
    assert float(exact_sample_std(values)) > 0
    with np.errstate(under=policy), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="zero stability dispersion"):
            parameter_stability(values)
        assert np.geterr() == before
    assert any("underflow" in str(item.message) for item in caught) == (policy == "warn")


def test_native_raise_preempts_guard_and_keeps_policy() -> None:
    with np.errstate(under="raise"):
        before = np.geterr().copy()
        with pytest.raises(FloatingPointError, match="underflow"):
            parameter_stability([1e-200, 2e-200])
        assert np.geterr() == before


@pytest.mark.parametrize("values", [[1e-200, 1e-200], [0.0, -0.0], [-2.0, -2.0]])
def test_exact_constants_and_signed_zero_retain_zero(values: list[float]) -> None:
    with np.errstate(all="raise"):
        result = parameter_stability(values)
    assert result.std_sharpe == 0 and result.stability_score == 1


def test_ordinary_and_positive_partial_underflow_controls_remain_exact() -> None:
    ordinary = parameter_stability([1.0, 2.0])
    assert ordinary.std_sharpe == 0.7071067811865476
    assert ordinary.stability_score == 0.6796227591281163
    with np.errstate(under="warn"), pytest.warns(RuntimeWarning, match="underflow"):
        partial = parameter_stability([1e-160, 2e-160])
    assert partial.std_sharpe == 7.0710284513028335e-161
    assert partial.stability_score == 1.0


def test_conservative_extreme_subnormal_domain_refuses_even_when_oracle_rounds_zero() -> None:
    values = [0.0, 0.0, 0.0, 0.0, math.ulp(0.0)]
    assert float(exact_sample_std(values)) == 0.0
    with np.errstate(under="ignore"), pytest.raises(ValueError, match="zero stability dispersion"):
        parameter_stability(values)


@pytest.mark.parametrize(
    "values,match",
    [([], "need >= 2"), ([True, False], "nonboolean"), ([1.0, float("nan")], "finite real")],
)
def test_original_validation_precedes_array_conversion(
    values: list[Any],
    match: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid originals reached conversion or zero-dispersion guard")

    monkeypatch.setattr(np, "asarray", forbidden)
    with pytest.raises(ValueError, match=match):
        parameter_stability(values)


def test_nonfinite_reduction_guard_precedes_zero_check(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("nonfinite reduction reached exact equality check")

    monkeypatch.setattr(np, "all", forbidden)
    with (
        np.errstate(over="ignore", invalid="ignore"),
        pytest.raises(ValueError, match="stability reductions must be finite"),
    ):
        parameter_stability([1e155, 2e155])


@given(exponent=st.integers(600, 1000), negative=st.booleans())
def test_binary_scaled_unequal_observations_have_positive_exact_representable_std(
    exponent: int,
    negative: bool,
) -> None:
    value = math.ldexp(-1.0 if negative else 1.0, -exponent)
    values = [value, 2 * value]
    assert float(exact_sample_std(values)) > 0
    with np.errstate(under="ignore"), pytest.raises(ValueError, match="zero stability dispersion"):
        parameter_stability(values)
