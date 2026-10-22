"""ADR-345: finite source history must not publish lost universe-bar evidence."""

import math
import warnings
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import cast

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.lab.universe import expected_max_sharpe_under_null


@pytest.mark.parametrize(
    "history",
    [float.fromhex("0x0.0000000000001p-1022"), 1e-320, np.longdouble("1e400")],
)
def test_universe_bar_refuses_lost_result_with_representable_exact_model(history: object) -> None:
    duration = cast(float, history)
    numerator, denominator = duration.as_integer_ratio()
    with localcontext() as context:
        context.prec = 160
        oracle = (Decimal(2) * Decimal(607).ln() * Decimal(denominator) / Decimal(numerator)).sqrt()
    assert math.isfinite(float(oracle)) and float(oracle) > 0
    with pytest.raises(ValueError, match="universe bar must be finite and positive"):
        expected_max_sharpe_under_null(607, duration)


@pytest.mark.parametrize(
    "n_symbols", [math.nan, math.inf, np.float64(math.nan), np.float64(math.inf)]
)
def test_universe_bar_refuses_active_nonfinite_selection_result(n_symbols: object) -> None:
    with pytest.raises(ValueError, match="universe bar must be finite and positive"):
        expected_max_sharpe_under_null(cast(int, n_symbols), 4.3)


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_universe_bar_preserves_native_tiny_history_warning_and_error(policy: str) -> None:
    duration = np.float64(1e-320)
    with np.errstate(over=policy), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if policy == "raise":
            with pytest.raises(FloatingPointError, match="overflow"):
                expected_max_sharpe_under_null(607, duration)
        else:
            with pytest.raises(ValueError, match="universe bar must be finite and positive"):
                expected_max_sharpe_under_null(607, duration)
        assert len(caught) == (1 if policy == "warn" else 0)
        if caught:
            assert issubclass(caught[0].category, RuntimeWarning)
            assert "overflow" in str(caught[0].message)


@pytest.mark.parametrize("n_symbols", [0, 1, 1.5, False, -math.inf])
@pytest.mark.parametrize("history", [1e-320, np.longdouble("1e400"), 4.3])
def test_universe_bar_retains_no_selection_zero(n_symbols: object, history: object) -> None:
    assert expected_max_sharpe_under_null(cast(int, n_symbols), cast(float, history)) == 0


@pytest.mark.parametrize("history", [0.0, -0.0, -1, -(10**400), np.longdouble("-1e400")])
def test_universe_bar_retains_nonpositive_history_zero(history: object) -> None:
    assert expected_max_sharpe_under_null(607, cast(float, history)) == 0


@pytest.mark.parametrize(
    "history",
    [True, Fraction(4, 3), np.float32(4.3), np.array(4.3), np.longdouble(np.finfo(float).max) * 2],
)
def test_universe_bar_preserves_native_positive_product(history: object) -> None:
    duration = cast(float, history)
    expected = math.sqrt(1.0 / duration) * math.sqrt(2.0 * math.log(607))
    assert expected > 0 and math.isfinite(expected)
    assert expected_max_sharpe_under_null(607, duration) == expected


@given(n_symbols=st.integers(2, 10000), significand=st.integers(1, 2047))
@settings(max_examples=40)
def test_universe_bar_refuses_overflow_despite_finite_positive_model(
    n_symbols: int, significand: int
) -> None:
    duration = math.ldexp(float(significand), -1074)
    numerator, denominator = duration.as_integer_ratio()
    with localcontext() as context:
        context.prec = 100
        oracle = (
            Decimal(2) * Decimal(n_symbols).ln() * Decimal(denominator) / Decimal(numerator)
        ).sqrt()
    assert math.isfinite(float(oracle)) and float(oracle) > 0
    with pytest.raises(ValueError, match="universe bar must be finite and positive"):
        expected_max_sharpe_under_null(n_symbols, duration)


@given(n_symbols=st.integers(2, 10000), years=st.floats(1e-4, 1e4))
@settings(max_examples=40)
def test_universe_bar_measurable_results_match_independent_decimal_model(
    n_symbols: int, years: float
) -> None:
    numerator, denominator = years.as_integer_ratio()
    with localcontext() as context:
        context.prec = 100
        oracle = (
            Decimal(2) * Decimal(n_symbols).ln() * Decimal(denominator) / Decimal(numerator)
        ).sqrt()
    actual = expected_max_sharpe_under_null(n_symbols, years)
    assert 0 < actual < math.inf
    assert actual == pytest.approx(float(oracle), rel=1e-14, abs=0)
