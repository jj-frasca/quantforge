"""ADR-388 deterministic construction controls; no original source draws."""

import importlib
import importlib.util
import math
from collections.abc import Iterator, Sequence
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st


def _prices(codes: object) -> np.ndarray:
    name = "app.research.lab.alternating_null"
    assert importlib.util.find_spec(name) is not None, "deterministic price kernel is missing"
    return importlib.import_module(name).alternating_skew_prices(codes)


def test_alternating_prices_round_each_transition_in_order() -> None:
    np.testing.assert_array_equal(_prices([0, 0]), [128.0, 130.0, 127.96875])


def _oracle(codes: Sequence[int]) -> np.ndarray:
    current = 128.0
    values = [current]
    for offset, category in enumerate(codes):
        # Independently encode simple returns, then round the exact product each step.
        a = Fraction(1, 128)
        change = (
            (2 * a if category == 0 else -a)
            if offset % 2 == 0
            else (-2 * a if category == 0 else a)
        )
        current = float(Fraction.from_float(current) * (1 + change))
        values.append(current)
    return np.asarray(values, dtype=np.float64)


@pytest.mark.parametrize(
    "codes,expected",
    [
        ([], [128.0]),
        ([0], [128.0, 130.0]),
        ([1], [128.0, 127.0]),
        ([2], [128.0, 127.0]),
        ([1, 1], [128.0, 127.0, 127.9921875]),
        ([2, 2], [128.0, 127.0, 127.9921875]),
    ],
)
def test_alternating_prices_exact_short_controls(codes: list[int], expected: list[float]) -> None:
    actual = _prices(codes)
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == np.dtype(np.float64)
    assert actual.shape == (len(codes) + 1,)
    assert actual.flags.c_contiguous


@pytest.mark.parametrize("factory", [tuple, list, range])
def test_alternating_prices_support_ordinary_sequences(factory: object) -> None:
    codes = factory(3) if factory is range else factory([0, 1, 2])
    np.testing.assert_array_equal(_prices(codes), _oracle([0, 1, 2]))


@pytest.mark.parametrize(
    "codes",
    [
        None,
        "",
        "012",
        b"",
        b"012",
        bytearray(),
        {},
        {0: 1},
        {0, 1},
        iter([0, 1]),
        np.array([], dtype=np.int64),
        np.array([0, 1]),
        np.array(0),
        0,
        True,
    ],
)
def test_alternating_prices_refuse_unsupported_containers(codes: object) -> None:
    with pytest.raises(ValueError, match="codes"):
        _prices(codes)


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        np.bool_(True),
        1.0,
        math.nan,
        math.inf,
        -math.inf,
        -1,
        3,
        2**100,
        np.uint64(2**64 - 1),
        "0",
        None,
        0j,
        Fraction(0),
        Decimal(0),
        [0],
        np.array([0]),
    ],
)
def test_alternating_prices_refuse_original_invalid_codes(value: object) -> None:
    with pytest.raises(ValueError, match=r"codes\[2\]"):
        _prices([0, 1, value])


def test_alternating_prices_maximum_count_precedes_element_validation() -> None:
    with pytest.raises(ValueError, match=r"codes.*7399"):
        _prices([True] * 7400)


def test_alternating_prices_bound_applies_to_the_actual_snapshot() -> None:
    class Growing(list[int]):
        def __iter__(self) -> Iterator[int]:
            self.append(0)
            return super().__iter__()

    with pytest.raises(ValueError, match=r"codes.*7399"):
        _prices(Growing([0] * 7399))


def test_alternating_prices_accept_numpy_integrals_in_sequence() -> None:
    np.testing.assert_array_equal(
        _prices([np.int64(0), np.uint8(1), np.int32(2)]), _oracle([0, 1, 2])
    )


@pytest.mark.parametrize("pattern", ["zero", "one", "cycle", "minimum", "maximum"])
def test_alternating_prices_full_horizon_matches_independent_rounding(pattern: str) -> None:
    if pattern == "zero":
        codes = [0] * 7399
    elif pattern == "one":
        codes = [1] * 7399
    elif pattern == "cycle":
        codes = [i % 3 for i in range(7399)]
    elif pattern == "minimum":
        codes = [1 if i % 2 == 0 else 0 for i in range(7399)]
    else:
        codes = [0 if i % 2 == 0 else 1 for i in range(7399)]
    actual = _prices(codes)
    np.testing.assert_array_equal(actual.view(np.uint64), _oracle(codes).view(np.uint64))
    assert len(actual) == 7400
    assert np.all(actual > 2.0**-226) and np.all(actual < 2.0**240)


@given(st.lists(st.integers(min_value=0, max_value=2), max_size=256))
def test_alternating_prices_controlled_codes_match_per_step_oracle(codes: list[int]) -> None:
    before = codes.copy()
    result = _prices(codes)
    np.testing.assert_array_equal(result.view(np.uint64), _oracle(codes).view(np.uint64))
    assert codes == before
    np.testing.assert_array_equal(result, _prices(codes))
    for cut in {0, len(codes) // 2, len(codes)}:
        np.testing.assert_array_equal(result[: cut + 1], _prices(codes[:cut]))
    alternate = [0 if x else 2 for x in codes]
    np.testing.assert_array_equal(_prices(codes + alternate)[: len(codes) + 1], result)
    remapped = [0 if x == 0 else 3 - x for x in codes]
    np.testing.assert_array_equal(result, _prices(remapped))


def test_alternating_prices_outputs_and_inputs_own_separate_state() -> None:
    codes = [0, 1, 2]
    first = _prices(codes)
    second = _prices(codes)
    first[:] = 1.0
    codes[:] = [2, 2, 2]
    np.testing.assert_array_equal(second, _oracle([0, 1, 2]))
    assert not np.shares_memory(first, second)


def test_alternating_prices_sequence_is_snapshotted_once() -> None:
    class Once(Sequence[int]):
        def __init__(self) -> None:
            self.reads = [0, 0, 0]

        def __len__(self) -> int:
            return 3

        def __getitem__(self, index: int) -> int:
            if not 0 <= index < 3:
                raise IndexError(index)
            self.reads[index] += 1
            assert self.reads[index] == 1, "caller sequence read again"
            return index

    codes = Once()
    np.testing.assert_array_equal(_prices(codes), _oracle([0, 1, 2]))
    assert codes.reads == [1, 1, 1]


@given(odd=st.booleans(), position=st.integers(-100, 100))
def test_alternating_ideal_conditional_moments(odd: bool, position: int) -> None:
    a = Fraction(1, 128)
    returns = (2 * a, -a, -a) if odd else (-2 * a, a, a)
    assert sum(returns, Fraction(0)) / 3 == 0
    assert sum(x * x for x in returns) / 3 == Fraction(1, 8192)
    assert sum(x**3 for x in returns) / 3 == (1 if odd else -1) * Fraction(1, 1048576)
    assert sum(Fraction(position, 100) * x for x in returns) / 3 == 0


@given(
    price=st.floats(min_value=2.0**-226, max_value=2.0**240, allow_nan=False, allow_infinity=False),
    odd=st.booleans(),
)
def test_alternating_native_conditional_mean_bias_bound(price: float, odd: bool) -> None:
    factors = (65 / 64, 127 / 128, 127 / 128) if odd else (63 / 64, 129 / 128, 129 / 128)
    returns = [(price * factor) / price - 1.0 for factor in factors]
    mean = sum((Fraction.from_float(x) for x in returns), Fraction(0)) / 3
    u = Fraction(1, 2**53)
    assert abs(mean) <= 2 * u + u * u


def test_alternating_all_prefix_bounds_include_multiplication_rounding() -> None:
    u = Fraction(1, 2**53)
    assert 128 * (Fraction(63, 64) * (1 - u)) ** 7399 > Fraction(1, 2**226)
    assert 128 * (Fraction(65, 64) * (1 + u)) ** 7399 < 2**240
