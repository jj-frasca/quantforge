"""ADR-357: raw drawdown must describe complete real equity evidence."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.metrics import max_drawdown


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("slot", [0, 1, 2])
@pytest.mark.parametrize("dtype", ["float32", "float64", "Float32", "Float64"])
def test_drawdown_invalid_equity_at_any_position_refuses(bad: float, slot: int, dtype: str) -> None:
    values = [100.0, 120.0, 90.0]
    values[slot] = bad
    with pytest.raises(ValueError, match=r"equity.*finite.*complete"):
        max_drawdown(pd.Series(values, dtype=dtype))


@pytest.mark.parametrize("slot", [0, 1, 2])
@pytest.mark.parametrize("dtype", ["Int64", "UInt64", "Float32", "Float64"])
def test_drawdown_nullable_missing_equity_refuses(slot: int, dtype: str) -> None:
    equity = pd.Series([100, 120, 90], dtype=dtype)
    equity.iloc[slot] = pd.NA
    with pytest.raises(ValueError, match=r"equity.*finite.*complete"):
        max_drawdown(equity)


@pytest.mark.parametrize(
    "equity",
    [
        pd.Series([100 + 2j, 80 + 3j]),
        pd.Series([100, 80], dtype="complex128"),
        pd.Series([True, False]),
        pd.Series([True, False], dtype="boolean"),
        pd.Series([100, 80], dtype="object"),
        pd.Series(["100", "80"]),
        pd.Series([Decimal(100), Decimal(80)], dtype="object"),
    ],
)
def test_drawdown_nonreal_or_nonnumeric_source_refuses(equity: pd.Series) -> None:
    with pytest.raises(ValueError, match=r"equity.*real.*nonboolean.*numeric"):
        max_drawdown(equity)


@pytest.mark.parametrize("dtype", ["bool", "boolean", "complex128", "object", "string"])
def test_drawdown_malformed_empty_source_refuses(dtype: str) -> None:
    with pytest.raises(ValueError, match=r"equity.*real.*nonboolean.*numeric"):
        max_drawdown(pd.Series(dtype=dtype))


@pytest.mark.parametrize(
    "dtype", ["float16", "float32", "float64", "Float32", "Float64", "int64", "UInt64"]
)
def test_drawdown_complete_numeric_empty_keeps_zero(dtype: str) -> None:
    assert max_drawdown(pd.Series(dtype=dtype)) == 0.0


@pytest.mark.parametrize("dtype", ["float32", "float64", "Float32", "Float64", "int64", "UInt64"])
def test_drawdown_complete_equity_keeps_native_result_and_source(dtype: str) -> None:
    equity = pd.Series([100, 80, 120, 60], dtype=dtype)
    original = equity.copy(deep=True)
    assert max_drawdown(equity) == -0.5
    pd.testing.assert_series_equal(equity, original)


def test_drawdown_wider_finite_equity_is_not_narrowed_to_infinity() -> None:
    equity = pd.Series(np.array(["1e400", "8e399"], dtype=np.longdouble))
    assert np.isfinite(equity).all()
    assert max_drawdown(equity) == pytest.approx(-0.2)


@pytest.mark.parametrize("values", [[0.0, -1.0, -2.0], [-100.0, -80.0, -90.0]])
def test_drawdown_finite_signed_equity_keeps_prior_clamp(values: list[float]) -> None:
    expected = -1.0 if values[0] == 0.0 else 0.0
    assert max_drawdown(pd.Series(values)) == expected


def test_drawdown_finite_all_zero_derived_nan_is_outside_source_guard() -> None:
    assert np.isnan(max_drawdown(pd.Series([0.0, 0.0])))


def test_drawdown_sparse_numeric_keeps_existing_arithmetic_refusal() -> None:
    equity = pd.Series([100.0, 80.0], dtype=pd.SparseDtype("float64", 0.0))
    with pytest.raises(NotImplementedError, match="cummax"):
        max_drawdown(equity)


@given(values=st.lists(st.integers(1, 100_000), min_size=1, max_size=30))
@settings(max_examples=60, deadline=None)
def test_drawdown_positive_equity_matches_exact_peak_ratio_property(values: list[int]) -> None:
    peak = values[0]
    worst = Fraction(0)
    for value in values:
        peak = max(peak, value)
        worst = min(worst, Fraction(value, peak) - 1)
    result = max_drawdown(pd.Series(values, dtype="float64"))
    assert -1.0 <= result <= 0.0
    assert result == pytest.approx(float(worst), abs=2e-16)


@given(values=st.lists(st.integers(1, 100_000), min_size=1, max_size=20))
@settings(max_examples=40, deadline=None)
def test_drawdown_missing_observation_never_becomes_reduced_sample_property(
    values: list[int],
) -> None:
    equity = pd.Series([float(value) for value in values] + [np.nan])
    with pytest.raises(ValueError, match=r"equity.*finite.*complete"):
        max_drawdown(equity)
