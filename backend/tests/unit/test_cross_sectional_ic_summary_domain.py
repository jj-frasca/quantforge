"""IC summaries require original bounded coefficients (ADR-266 / FINDING-215)."""

import math
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.ic import rank_ic, summarize_ic


def _invalid(kind: str, negative: bool) -> object:
    if kind == "float":
        value = np.nextafter(1.0, np.inf)
    elif kind == "wide":
        value = np.nextafter(np.longdouble(1), np.longdouble(2))
    elif kind == "decimal":
        value = Decimal("1.0000000000000000000000000001")
        return value.copy_negate() if negative else value
    elif kind == "fraction":
        value = Fraction(10**100 + 1, 10**100)
    elif kind == "infinity":
        value = np.inf
    elif kind == "nan":
        value = np.nan
    elif kind == "missing":
        return pd.NA
    elif kind == "complex":
        value = complex(0.5, 0.5)
    else:
        return "0.5"
    return -value if negative else value


@pytest.mark.parametrize(
    "kind",
    ["float", "wide", "decimal", "fraction", "infinity", "nan", "missing", "complex", "string"],
)
@pytest.mark.parametrize("negative", [False, True])
@pytest.mark.parametrize("singleton", [False, True])
def test_summarize_ic_refuses_invalid_original_cells_before_conversion_or_shortcut(
    kind: str, negative: bool, singleton: bool
) -> None:
    invalid = _invalid(kind, negative)
    if kind in {"float", "wide", "decimal", "fraction"}:
        assert invalid < -1 if negative else invalid > 1
    values = [invalid] if singleton else [0.0, invalid]
    dtype = np.longdouble if kind == "wide" else np.complex128 if kind == "complex" else object
    series = pd.Series(values, dtype=dtype)
    with pytest.raises(ValueError, match="IC observations must be finite real values in"):
        summarize_ic(series)


def test_summarize_ic_refuses_invalid_cells_even_when_their_mean_is_bounded() -> None:
    with pytest.raises(ValueError, match="IC observations must be finite real values in"):
        summarize_ic(pd.Series([2.0, -2.0]))


@pytest.mark.parametrize("negative", [False, True])
def test_rank_ic_projects_perfect_derived_roundoff_before_strict_summary(negative: bool) -> None:
    n = 17
    growth = 1 + np.arange(1, n + 1) / 100
    prices = pd.DataFrame(np.vstack([np.ones(n), growth, growth * growth]))
    scores = np.arange(n)[::-1] if negative else np.arange(n)
    signals = pd.DataFrame(np.tile(scores, (3, 1)))
    actual = rank_ic(signals, prices)
    assert ((actual >= -1) & (actual <= 1)).all()
    np.testing.assert_allclose(actual, -1.0 if negative else 1.0, rtol=0, atol=0)
    summary = summarize_ic(actual)
    assert summary is not None
    assert summary.mean == (-1.0 if negative else 1.0)
    assert summary.n_periods == 2


@pytest.mark.parametrize(
    "kind", ["float64", "Float64", "longdouble", "bool", "fraction", "decimal"]
)
def test_summarize_ic_preserves_original_numeric_operands_and_statistics(kind: str) -> None:
    if kind == "fraction":
        series = pd.Series([Fraction(0), Fraction(1)])
    elif kind == "decimal":
        series = pd.Series([Decimal(0), Decimal(1)])
    else:
        series = pd.Series([0, 1], dtype=kind)
    before = series.copy(deep=True)
    state = np.geterr()
    with np.errstate(all="raise"):
        actual = summarize_ic(series)
    assert actual is not None
    assert actual.mean == 0.5 and actual.hit_rate == 0.5 and actual.n_periods == 2
    assert actual.std == pytest.approx(math.sqrt(0.5))
    assert actual.information_ratio == pytest.approx(math.sqrt(0.5))
    assert actual.t_stat == pytest.approx(1.0)
    pd.testing.assert_series_equal(series, before, check_exact=True)
    assert np.geterr() == state


@pytest.mark.parametrize("sign", [-1.0, 0.0, 1.0])
def test_summarize_ic_preserves_deliberate_constant_series_floor(sign: float) -> None:
    actual = summarize_ic(pd.Series([sign * 0.25] * 2))
    assert actual is not None
    assert actual.mean == sign * 0.25 and actual.std == 0.0
    assert actual.information_ratio == sign * 250_000_000_000.0
    assert actual.t_stat == sign * 250_000_000_000.0 * math.sqrt(2)
    assert actual.hit_rate == (1.0 if sign > 0 else 0.0)


@pytest.mark.parametrize("kind", ["float64", "Float64", "longdouble", "object", "complex128"])
def test_summarize_ic_preserves_empty_numeric_inputs(kind: str) -> None:
    assert summarize_ic(pd.Series([], dtype=kind)) is None


@pytest.mark.parametrize("value", [-1.0, 0.0, 1.0, Fraction(1, 3), Decimal("0.3")])
def test_summarize_ic_preserves_valid_singleton_none(value: object) -> None:
    assert summarize_ic(pd.Series([value])) is None


@given(values=st.lists(st.integers(-100, 100), min_size=2, max_size=30))
def test_summarize_ic_keeps_bounded_observations_mean_hit_and_count(values: list[int]) -> None:
    source = pd.Series([value / 100 for value in values])
    actual = summarize_ic(source)
    assert actual is not None
    assert -1 <= actual.mean <= 1
    assert 0 <= actual.hit_rate <= 1
    assert actual.n_periods == len(values)
    assert actual.mean == pytest.approx(
        float(sum(Fraction(value, 100) for value in values) / len(values)), rel=1e-14, abs=1e-15
    )
    assert actual.hit_rate == sum(value > 0 for value in values) / len(values)
    assert math.isfinite(actual.std) and actual.std >= 0
    assert math.isfinite(actual.information_ratio) and math.isfinite(actual.t_stat)


@given(
    rows=st.integers(1, 8),
    position=st.integers(0, 7),
    value=st.sampled_from([np.inf, -np.inf, np.nan, 2.0, -2.0, np.nextafter(1.0, np.inf)]),
)
def test_summarize_ic_never_hides_an_invalid_original_observation(
    rows: int, position: int, value: float
) -> None:
    source = pd.Series([0.0] * rows)
    source.iat[position % rows] = value
    with pytest.raises(ValueError, match="IC observations must be finite real values in"):
        summarize_ic(source)
