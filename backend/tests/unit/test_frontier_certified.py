"""Independent inverse-equation tests; no search, source generator or gate calls."""

import math
from collections.abc import Callable
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    Inexact,
    Rounded,
    localcontext,
)
from fractions import Fraction
from statistics import NormalDist
from typing import cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.special import ndtr, ndtri

from app.research.lab import frontier as f
from app.research.lab.universe import expected_max_sharpe_under_null


def oracle(n: int, T: float, p: float) -> float:
    # Independent monotone Decimal bisection, not quadratic root algebra.
    b = expected_max_sharpe_under_null(n, T)
    z = NormalDist().inv_cdf(p)
    if z == 0.0:
        return b
    with localcontext(Context(prec=300, rounding=ROUND_HALF_EVEN)):

        def d(x: float) -> Decimal:
            return Decimal.from_float(x)

        bd, td, zd = d(b), d(T), d(z)
        assert zd * zd < 504 * td

        def residual(s: Decimal) -> Decimal:
            return s - bd - zd * ((1 + s * s / 504) / td).sqrt()

        lo, hi = Decimal(-1), Decimal(1)
        while residual(lo) > 0:
            lo *= 2
        while residual(hi) < 0:
            hi *= 2
        for _ in range(600):
            mid = (lo + hi) / 2
            if residual(mid) < 0:
                lo = mid
            else:
                hi = mid
        return float((lo + hi) / 2)


def assert_root(n: int, T: float, p: float) -> float:
    expected = oracle(n, T, p)
    actual = f.detectable_sharpe(n, T, power=p)
    assert math.isfinite(actual)
    assert abs(actual - expected) <= 8 * math.ulp(expected)
    return actual


@pytest.mark.parametrize(
    "n,T,p",
    [
        (200, 0.01, 0.95),
        (200, 2 / 252, 0.8),
        (607, 2 / 252, 0.8),
        (607, 4.3, 0.8),
        (200, 4.3, 0.95),
        (1, 4.3, 1e-300),
        (1, 4.3, math.ulp(0.0)),
        (1, 4.3, math.nextafter(1.0, 0.0)),
        (200, 0.01, 0.25),
        (1, 4.3, 0.25),
        (0, 4.3, 0.8),
        (1, 4.3, 0.8),
        (607, 8.6, 0.8),
        (304, 4.3, 0.8),
    ],
)
def test_detectable_sharpe_matches_independent_equation_oracle(n: int, T: float, p: float) -> None:
    assert_root(n, T, p)


@pytest.mark.parametrize(
    "p", [math.ulp(0.0), 1e-300, 1e-50, 0.001, 0.25, 0.5, 0.8, 0.95, 0.99, math.nextafter(1.0, 0.0)]
)
def test_normal_quantile_matches_independent_scientific_tails(p: float) -> None:
    expected = float(ndtri(p))
    actual = f._normal_quantile(p)
    assert math.isfinite(actual)
    assert abs(actual - expected) <= 8 * math.ulp(expected)


@pytest.mark.parametrize(
    "n,T,p", [(200, 2 / 252, 0.99), (1, 0.001, 0.99), (200, 0.01, 0.001), (1, 0.001, 0.001)]
)
def test_detectable_sharpe_refuses_outside_supported_unique_inverse_regime(
    n: int, T: float, p: float
) -> None:
    with pytest.raises(ValueError):
        f.detectable_sharpe(n, T, power=p)


@pytest.mark.parametrize("n", [0, 1, 200, 607])
def test_detectable_sharpe_half_power_is_exact_unchanged_bar(n: int) -> None:
    assert f.detectable_sharpe(n, 4.3, power=0.5) == expected_max_sharpe_under_null(n, 4.3)


@pytest.mark.parametrize("p", [0.95, 0.99, 0.001, 0.25])
def test_detectable_sharpe_near_existence_boundary_uses_exact_coefficient_sign(p: float) -> None:
    z = NormalDist().inv_cdf(p)
    boundary = Fraction.from_float(z) ** 2 / 504
    T = float(boundary)
    while Fraction.from_float(T) <= boundary:
        T = math.nextafter(T, math.inf)
    assert_root(200, T, p)
    T = math.nextafter(float(boundary), 0.0)
    while Fraction.from_float(T) >= boundary:
        T = math.nextafter(T, 0.0)
    with pytest.raises(ValueError):
        f.detectable_sharpe(200, T, power=p)


@pytest.mark.parametrize("T", [float("nan"), float("inf"), -float("inf"), 0.0, -1.0])
@pytest.mark.parametrize("factory", [f.detectable_sharpe, f.describe_frontier])
def test_frontier_factories_refuse_nonfinite_or_nonpositive_history(
    T: float, factory: Callable[[int, float], object]
) -> None:
    with pytest.raises(ValueError, match="holdout_years"):
        factory(200, T)


@pytest.mark.parametrize("p", [float("nan"), float("inf"), -float("inf"), 0.0, 1.0])
def test_detectable_sharpe_refuses_invalid_power(p: float) -> None:
    with pytest.raises(ValueError, match="power"):
        f.detectable_sharpe(200, 4.3, power=p)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_detectable_sharpe_refuses_nonfinite_shared_bar_without_changing_it(
    monkeypatch: pytest.MonkeyPatch, value: float
) -> None:
    original = cast(Callable[[int, float], float], f.__dict__["expected_max_sharpe_under_null"])

    def fixed_bar(n: int, T: float) -> float:
        return value

    monkeypatch.setattr(f, "expected_max_sharpe_under_null", fixed_bar)
    with pytest.raises(ValueError):
        f.detectable_sharpe(200, 4.3)
    assert (
        cast(Callable[[int, float], float], f.__dict__["expected_max_sharpe_under_null"])
        is fixed_bar
    )
    assert original is expected_max_sharpe_under_null


def test_frontier_refuses_unchanged_standard_error_unrepresentability() -> None:
    with pytest.raises(ValueError):
        f.detectable_sharpe(1, math.ulp(0.0), power=0.5)


def test_describe_frontier_preserves_shared_functions_and_caller_state() -> None:
    bar = cast(Callable[[int, float], float], f.__dict__["expected_max_sharpe_under_null"])
    se = f.sharpe_standard_error
    args: dict[str, int | float] = {"n_symbols": 200, "holdout_years": 0.01, "power": 0.95}
    before = args.copy()
    result = f.describe_frontier(int(args["n_symbols"]), args["holdout_years"], power=args["power"])
    assert args == before
    assert (
        cast(Callable[[int, float], float], f.__dict__["expected_max_sharpe_under_null"]) is bar
        and f.sharpe_standard_error is se
    )
    assert result.bar == bar(200, 0.01)
    assert result.detectable_sharpe == oracle(200, 0.01, 0.95)
    assert result.standard_error == se(result.detectable_sharpe, 0.01)


@settings(max_examples=24, deadline=None, derandomize=True)
@given(
    n=st.integers(0, 10000),
    T=st.floats(0.1, 20.0, allow_nan=False, allow_infinity=False),
    p=st.floats(0.01, 0.99, allow_nan=False, allow_infinity=False),
)
def test_detectable_sharpe_certified_regime_matches_independent_root(
    n: int, T: float, p: float
) -> None:
    assert_root(n, T, p)


@pytest.mark.parametrize("p", [0.95, 0.25])
@pytest.mark.parametrize("precision,rounding", [(7, ROUND_FLOOR), (3, ROUND_CEILING)])
def test_detectable_sharpe_isolates_caller_decimal_context(
    p: float, precision: int, rounding: str
) -> None:
    expected = oracle(200, 0.01, p)
    with localcontext() as caller:
        caller.prec = precision
        caller.rounding = rounding
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        caller.clear_flags()
        before = (
            caller.prec,
            caller.rounding,
            caller.Emin,
            caller.Emax,
            caller.traps.copy(),
            caller.flags.copy(),
        )
        actual = f.detectable_sharpe(200, 0.01, power=p)
        assert actual == expected
        assert before == (
            caller.prec,
            caller.rounding,
            caller.Emin,
            caller.Emax,
            caller.traps.copy(),
            caller.flags.copy(),
        )


@pytest.mark.parametrize(
    "n,T,p",
    [
        (1, 4.3, math.nextafter(0.5, 0.0)),
        (1, 4.3, math.nextafter(0.5, 1.0)),
        (200, 4.3, float(ndtr(-math.sqrt(2 * math.log(200))))),
        (607, 8.6, float(ndtr(-math.sqrt(2 * math.log(607))))),
    ],
)
def test_detectable_sharpe_signed_near_zero_retains_cancellation_residual(
    n: int, T: float, p: float
) -> None:
    assert_root(n, T, p)
