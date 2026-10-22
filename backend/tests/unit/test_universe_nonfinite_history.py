"""ADR-344: undefined history cannot become a zero annotation bar."""

from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from typing import cast

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.lab.universe import expected_max_sharpe_under_null


@pytest.mark.parametrize("n_symbols", [0, 1, 2, 607])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize(
    "factory",
    [
        float,
        np.float16,
        np.float32,
        np.float64,
        np.longdouble,
        pytest.param(lambda value: np.array(value, dtype=float), id="zero_dimensional"),
    ],
)
def test_universe_bar_refuses_nonfinite_history_before_shortcuts(
    n_symbols: int, value: float, factory: Callable[[float], object]
) -> None:
    history = cast(float, factory(value))
    with pytest.raises(ValueError, match="holdout_years must be finite"):
        expected_max_sharpe_under_null(n_symbols, history)


@pytest.mark.parametrize("n_symbols", [0, 1, 2, 607])
@pytest.mark.parametrize(
    "history",
    [
        0.0,
        -0.0,
        -1.0,
        Fraction(-1, 10**400),
        -(10**400),
        np.float32(-3),
        np.longdouble("-1e400"),
        Decimal("0"),
    ],
)
def test_universe_bar_retains_native_finite_nonpositive_history_shortcut(
    n_symbols: int, history: object
) -> None:
    assert expected_max_sharpe_under_null(n_symbols, cast(float, history)) == 0.0


@pytest.mark.parametrize("n_symbols", [0, 1])
@pytest.mark.parametrize(
    "history",
    [4.3, False, True, Fraction(4, 3), np.array(4.3), np.longdouble(np.finfo(float).max) * 2],
)
def test_universe_bar_retains_finite_no_selection_shortcut(n_symbols: int, history: object) -> None:
    assert expected_max_sharpe_under_null(n_symbols, cast(float, history)) == 0.0


@pytest.mark.parametrize("history", [False, True])
def test_universe_bar_does_not_add_a_boolean_duration_policy(history: bool) -> None:
    assert expected_max_sharpe_under_null(607, history) == expected_max_sharpe_under_null(
        607, float(history)
    )


def test_universe_bar_preserves_positive_native_wide_history_without_float_conversion() -> None:
    history = np.longdouble(np.finfo(float).max) * 2
    assert np.isfinite(history)
    assert history > np.longdouble(np.finfo(float).max)
    value = expected_max_sharpe_under_null(607, history)
    assert np.isfinite(value) and value > 0
    assert value == pytest.approx(1.8880843389847055e-154, rel=1e-14, abs=0)


@given(n_symbols=st.integers(0, 10000), history=st.sampled_from([np.nan, np.inf, -np.inf]))
@settings(max_examples=30)
def test_universe_bar_never_interprets_nonfinite_history_as_a_measured_bar(
    n_symbols: int, history: float
) -> None:
    with pytest.raises(ValueError, match="holdout_years must be finite"):
        expected_max_sharpe_under_null(n_symbols, history)


@given(
    n_symbols=st.integers(2, 10000),
    years=st.floats(1e-4, 1e4, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30)
def test_universe_bar_retains_inverse_square_root_history_scaling(
    n_symbols: int, years: float
) -> None:
    original = expected_max_sharpe_under_null(n_symbols, years)
    longer = expected_max_sharpe_under_null(n_symbols, 4 * years)
    assert original > 0 and longer > 0
    assert longer == pytest.approx(original / 2, rel=2e-15, abs=0)
