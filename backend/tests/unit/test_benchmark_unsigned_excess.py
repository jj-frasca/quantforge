"""Unsigned differences are exact signed evidence, not modular arithmetic (ADR-273)."""

from decimal import Decimal, localcontext
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator
from app.research.benchmarks.comparator import BenchmarkComparator

_UNSIGNED = ["uint8", "uint16", "uint32", "uint64", "UInt8", "UInt16", "UInt32", "UInt64"]


def _oracle(differences: list[int]) -> tuple[float, float]:
    values = [Fraction(value) for value in differences]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance == 0:
        return 0.0, 0.0
    with localcontext() as context:
        context.prec = 100
        std = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        root = Decimal.from_float(float(np.sqrt(252)))
        return (
            float(root * Decimal(mean.numerator) / Decimal(mean.denominator) / std),
            float(root * std),
        )


@pytest.mark.parametrize("left", _UNSIGNED)
@pytest.mark.parametrize("right", _UNSIGNED)
@pytest.mark.parametrize(
    "strategy_values,benchmark_values",
    [
        ([0, 1, 2], [1, 2, 3]),
        ([0, 3, 2], [1, 2, 4]),
        ([1, 2, 3], [0, 1, 2]),
        ([1, 2, 3], [1, 2, 3]),
    ],
)
def test_unsigned_pair_excess_matches_exact_signed_difference(
    left: str, right: str, strategy_values: list[int], benchmark_values: list[int]
) -> None:
    strategy = pd.Series(strategy_values, dtype=left, name="return")
    benchmark = pd.Series(benchmark_values, dtype=right, name="return")
    differences = [a - b for a, b in zip(strategy_values, benchmark_values, strict=True)]
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    expected = pd.Series(differences, dtype=np.longdouble, name="return")
    pd.testing.assert_series_equal(result.excess_returns, expected)
    expected_ir, expected_te = _oracle(differences)
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
    if any(value < 0 for value in differences) and expected_ir < 0:
        assert result.information_ratio < 0


@pytest.mark.parametrize("left", ["uint64", "UInt64"])
@pytest.mark.parametrize("right", ["uint64", "UInt64"])
@pytest.mark.parametrize("reverse", [False, True])
def test_unsigned_large_neighbors_subtract_before_encoding(
    left: str, right: str, reverse: bool
) -> None:
    maximum = int(np.iinfo(np.uint64).max)
    strategy = pd.Series([maximum] * 3, dtype=left)
    benchmark = pd.Series([maximum - 1] * 3, dtype=right)
    if reverse:
        strategy, benchmark = benchmark, strategy
    result = BenchmarkComparator().compare(strategy, benchmark)
    expected = pd.Series([-1 if reverse else 1] * 3, dtype=np.longdouble)
    pd.testing.assert_series_equal(result.excess_returns, expected)
    assert result.information_ratio == result.tracking_error == 0


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("dtype", ["uint64", "UInt64"])
def test_unsigned_maximum_difference_requires_exact_native_encoding(
    reverse: bool, dtype: str
) -> None:
    maximum = int(np.iinfo(np.uint64).max)
    strategy = pd.Series([maximum] * 3, dtype=dtype)
    benchmark = pd.Series([0] * 3, dtype=dtype)
    if reverse:
        strategy, benchmark = benchmark, strategy
    difference = -maximum if reverse else maximum
    representable = np.longdouble(difference).as_integer_ratio() == (difference, 1)
    if representable:
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert all(value.as_integer_ratio() == (difference, 1) for value in result.excess_returns)
        assert result.excess_returns.dtype == np.dtype(np.longdouble)
        assert result.information_ratio == result.tracking_error == 0
    else:
        with pytest.raises(ValueError, match=r"unsigned excess.*exactly representable"):
            BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize(
    "names",
    [
        ("r", "r"),
        ("left", "right"),
        (np.nan, np.nan),
        (pd.NA, pd.NA),
        (7, 7),
        (("return", 1), ("return", 1)),
    ],
)
@pytest.mark.parametrize("left,right", [("uint8", "UInt16"), ("UInt16", "uint8")])
def test_unsigned_excess_preserves_alignment_metadata_and_sources(
    names: tuple[object, object], left: str, right: str
) -> None:
    strategy = pd.Series([9, 0, 3, 2], index=[0, 1, 2, 3], dtype=left, name=names[0])
    benchmark = pd.Series([1, 2, 4, 8], index=[1, 2, 3, 4], dtype=right, name=names[1])
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    name = (pd.Series(dtype=float, name=names[0]) - pd.Series(dtype=float, name=names[1])).name
    result = BenchmarkComparator().compare(strategy, benchmark)
    expected = pd.Series([-1, 1, -2], index=[1, 2, 3], dtype=np.longdouble, name=name)
    pd.testing.assert_series_equal(result.excess_returns, expected)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("missing_side", ["strategy", "benchmark"])
def test_unsigned_excess_aligned_missing_still_refuses(missing_side: str) -> None:
    strategy = pd.Series([0, 3, 2], dtype="UInt8")
    benchmark = pd.Series([1, 2, 4], dtype="UInt16")
    (strategy if missing_side == "strategy" else benchmark).iloc[1] = pd.NA
    with pytest.raises(ValueError, match="finite"):
        BenchmarkComparator().compare(strategy, benchmark)


def test_unsigned_excess_unaligned_missing_does_not_change_evidence() -> None:
    strategy = pd.Series([pd.NA, 0, 3, 2], index=[0, 1, 2, 3], dtype="UInt8")
    benchmark = pd.Series([1, 2, 4, pd.NA], index=[1, 2, 3, 4], dtype="UInt16")
    result = BenchmarkComparator().compare(strategy, benchmark)
    pd.testing.assert_series_equal(
        result.excess_returns, pd.Series([-1, 1, -2], index=[1, 2, 3], dtype=np.longdouble)
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_unsigned_excess_encoding_certification_refuses_lost_integer_evidence(
    reverse: bool,
) -> None:
    maximum = int(np.iinfo(np.uint64).max)
    original_asarray = np.asarray

    def constrained_encoding(values: object, *args: object, **kwargs: object) -> np.ndarray:
        # Constrain just the helper's explicit encoding; pandas keeps real NumPy behavior.
        if isinstance(values, list) and not args and kwargs.get("dtype") is np.longdouble:
            return original_asarray(values, dtype=np.float64)
        return original_asarray(values, *args, **kwargs)

    strategy = pd.Series([maximum] * 3, dtype="uint64")
    benchmark = pd.Series([0] * 3, dtype="UInt64")
    neighbor = pd.Series([maximum - 1] * 3, dtype="UInt64")
    difference = -maximum if reverse else maximum
    assert np.float64(difference).as_integer_ratio() != (difference, 1)
    if reverse:
        strategy, benchmark = benchmark, strategy
        near_strategy, near_benchmark = neighbor, benchmark
    else:
        near_strategy, near_benchmark = strategy, neighbor
    with patch.object(comparator.np, "asarray", side_effect=constrained_encoding):
        with pytest.raises(ValueError, match=r"unsigned excess.*exactly representable"):
            comparator._exact_unsigned_excess(strategy, benchmark)
        excess = comparator._exact_unsigned_excess(near_strategy, near_benchmark)
    assert list(excess) == [-1 if reverse else 1] * 3


@settings(max_examples=80, deadline=None)
@given(
    pairs=st.lists(st.tuples(st.integers(0, 127), st.integers(0, 127)), min_size=2, max_size=20),
    left=st.sampled_from(_UNSIGNED),
    right=st.sampled_from(_UNSIGNED),
)
def test_unsigned_excess_property_retains_exact_sign_and_dispersion(
    pairs: list[tuple[int, int]], left: str, right: str
) -> None:
    strategy = pd.Series([pair[0] for pair in pairs], dtype=left)
    benchmark = pd.Series([pair[1] for pair in pairs], dtype=right)
    differences = [a - b for a, b in pairs]
    result = BenchmarkComparator().compare(strategy, benchmark)
    pd.testing.assert_series_equal(
        result.excess_returns, pd.Series(differences, dtype=np.longdouble)
    )
    expected_ir, expected_te = _oracle(differences)
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
