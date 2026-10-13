"""Mixed signed/unsigned integer excess retains original differences (ADR-274)."""

from decimal import Decimal, localcontext
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator, BenchmarkComparison

_UNSIGNED = ["uint8", "uint16", "uint32", "uint64", "UInt8", "UInt16", "UInt32", "UInt64"]
_SIGNED = ["int8", "int16", "int32", "int64", "Int8", "Int16", "Int32", "Int64"]


def _assert_exact(result: BenchmarkComparison, differences: list[int]) -> None:
    assert all(
        value.as_integer_ratio() == (difference, 1)
        for value, difference in zip(result.excess_returns, differences, strict=True)
    )
    assert result.excess_returns.dtype == np.dtype(np.longdouble)
    values = [Fraction(value) for value in differences]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance == 0:
        assert result.information_ratio == result.tracking_error == 0
        return
    with localcontext() as context:
        context.prec = 100
        std = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        root = Decimal.from_float(float(np.sqrt(252)))
        expected_ir = float(root * Decimal(mean.numerator) / Decimal(mean.denominator) / std)
        expected_te = float(root * std)
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)


@pytest.mark.parametrize("unsigned", _UNSIGNED)
@pytest.mark.parametrize("signed", _SIGNED)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "a,b",
    [
        ([0, 3, 2], [1, 2, 4]),
        ([0, 1, 2], [1, 2, 3]),
        ([1, 2, 3], [0, 1, 2]),
        ([1, 2, 3], [1, 2, 3]),
    ],
)
def test_mixed_integer_excess_matches_exact_original_difference(
    unsigned: str, signed: str, reverse: bool, a: list[int], b: list[int]
) -> None:
    strategy, benchmark = pd.Series(a, dtype=unsigned), pd.Series(b, dtype=signed)
    if reverse:
        strategy, benchmark = benchmark, strategy
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    differences = [int(x) - int(y) for x, y in zip(strategy, benchmark, strict=True)]
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    _assert_exact(result, differences)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("unsigned", ["uint64", "UInt64"])
@pytest.mark.parametrize("signed", ["int64", "Int64"])
@pytest.mark.parametrize("reverse", [False, True])
def test_mixed_large_integer_excess_survives_operand_float_promotion(
    unsigned: str, signed: str, reverse: bool
) -> None:
    base = int(np.iinfo(np.int64).max) - 4
    strategy = pd.Series([base, base + 3, base + 2], dtype=unsigned)
    benchmark = pd.Series([base + 1, base + 2, base + 4], dtype=signed)
    if reverse:
        strategy, benchmark = benchmark, strategy
    result = BenchmarkComparator().compare(strategy, benchmark)
    _assert_exact(result, [1, -1, 2] if reverse else [-1, 1, -2])
    assert result.information_ratio != 0
    assert result.tracking_error > 0


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("unsigned", ["uint64", "UInt64"])
@pytest.mark.parametrize("signed", ["int64", "Int64"])
def test_mixed_integer_maximum_excess_requires_exact_native_encoding(
    reverse: bool, unsigned: str, signed: str
) -> None:
    maximum = int(np.iinfo(np.uint64).max)
    strategy, benchmark = pd.Series([maximum] * 3, dtype=unsigned), pd.Series([0] * 3, dtype=signed)
    if reverse:
        strategy, benchmark = benchmark, strategy
    difference = -maximum if reverse else maximum
    if np.longdouble(difference).as_integer_ratio() == (difference, 1):
        _assert_exact(BenchmarkComparator().compare(strategy, benchmark), [difference] * 3)
    else:
        with pytest.raises(ValueError, match=r"unsigned excess.*exactly representable"):
            BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "names",
    [("r", "r"), (np.nan, np.nan), (pd.NA, pd.NA), (7, 7), (("r", 1), ("r", 1)), ("a", "b")],
)
def test_mixed_integer_excess_preserves_partial_overlap_and_metadata(
    reverse: bool, names: tuple[object, object]
) -> None:
    strategy = pd.Series([pd.NA, 0, 3, 2], index=[0, 1, 2, 3], dtype="UInt64", name=names[0])
    benchmark = pd.Series([1, 2, 4, pd.NA], index=[1, 2, 3, 4], dtype="Int64", name=names[1])
    if reverse:
        strategy, benchmark = benchmark, strategy
    name = (
        pd.Series(dtype=float, name=strategy.name) - pd.Series(dtype=float, name=benchmark.name)
    ).name
    result = BenchmarkComparator().compare(strategy, benchmark)
    expected = pd.Series(
        [1, -1, 2] if reverse else [-1, 1, -2], index=[1, 2, 3], dtype=np.longdouble, name=name
    )
    pd.testing.assert_series_equal(result.excess_returns, expected)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("invalid", [-1, -2, pd.NA])
def test_mixed_integer_original_source_guard_precedes_exact_difference(
    reverse: bool, invalid: object
) -> None:
    strategy = pd.Series([0, 3, 2], dtype="UInt8")
    benchmark = pd.Series([1, invalid, 4], dtype="Int8")
    if reverse:
        strategy, benchmark = benchmark, strategy
    with (
        patch(
            "app.research.benchmarks.comparator._exact_unsigned_excess",
            side_effect=AssertionError("must validate originals first"),
        ),
        pytest.raises(ValueError, match="finite" if invalid is pd.NA else "positive wealth"),
    ):
        BenchmarkComparator().compare(strategy, benchmark)


@settings(max_examples=80, deadline=None)
@given(
    pairs=st.lists(st.tuples(st.integers(0, 127), st.integers(0, 127)), min_size=2, max_size=20),
    unsigned=st.sampled_from(_UNSIGNED),
    signed=st.sampled_from(_SIGNED),
    reverse=st.booleans(),
)
def test_mixed_integer_excess_property_retains_exact_signed_evidence(
    pairs: list[tuple[int, int]], unsigned: str, signed: str, reverse: bool
) -> None:
    strategy = pd.Series([a for a, _ in pairs], dtype=unsigned)
    benchmark = pd.Series([b for _, b in pairs], dtype=signed)
    if reverse:
        strategy, benchmark = benchmark, strategy
    differences = [int(a) - int(b) for a, b in zip(strategy, benchmark, strict=True)]
    _assert_exact(BenchmarkComparator().compare(strategy, benchmark), differences)
