"""ADR-332: original count evidence precedes expanding-window row arithmetic."""

from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.walk_forward import walk_forward_splits

INTEGER_TYPES = [
    int,
    np.int8,
    np.int16,
    np.int32,
    np.int64,
    np.uint8,
    np.uint16,
    np.uint32,
    np.uint64,
]


@pytest.mark.parametrize("base", [2.5, np.float64(2.5), Fraction(5, 2)])
def test_fractional_start_refuses_instead_of_overlapping_rows(base: Any) -> None:
    with pytest.raises(ValueError, match="min_train"):
        walk_forward_splits(10, 2, base)


@pytest.mark.parametrize(
    "args,message",
    [
        ((10, np.uint8(255), 1), "n_obs must be >= n_splits"),
        ((np.uint8(250), 2, np.uint8(200)), "min_train too large"),
        ((10, 2, np.uint8(255)), "min_train too large"),
    ],
)
def test_unsigned_geometry_cannot_wrap_past_room_checks(
    args: tuple[Any, Any, Any],
    message: str,
) -> None:
    with np.errstate(over="ignore"), pytest.raises(ValueError, match=message):
        walk_forward_splits(*args)


@pytest.mark.parametrize("parameter", ["n_obs", "n_splits", "min_train"])
@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        np.bool_(True),
        2.0,
        np.float64(2),
        Fraction(2),
        "2",
        2 + 0j,
        [2],
        np.array(2),
        np.array([2]),
        float("nan"),
        float("inf"),
        -1,
        np.int64(-1),
    ],
)
def test_original_noncounts_refuse_before_row_generation(parameter: str, bad: Any) -> None:
    args = {"n_obs": 10, "n_splits": 2, "min_train": 2}
    args[parameter] = bad
    with pytest.raises(ValueError, match=parameter):
        walk_forward_splits(**args)


@pytest.mark.parametrize(
    "args,message",
    [
        ((-1, 0, -1), "n_splits must be >= 1"),
        ((0, 1, -1), "n_obs must be >= n_splits"),
        ((10, 2, 0), "min_train must be >= 1"),
        ((10, 2, 9), "min_train too large"),
    ],
)
def test_existing_count_check_precedence(args: tuple[int, int, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        walk_forward_splits(*args)


def test_none_keeps_the_default_fold_and_remainder() -> None:
    splits = walk_forward_splits(11, 3, None)
    assert [(a.tolist(), b.tolist()) for a, b in splits] == [
        ([0, 1], [2, 3]),
        ([0, 1, 2, 3], [4, 5]),
        ([0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10]),
    ]


@given(
    n=st.integers(2, 90),
    raw_k=st.integers(1, 89),
    raw_base=st.integers(0, 90),
    default=st.booleans(),
    n_type=st.sampled_from(INTEGER_TYPES),
    k_type=st.sampled_from(INTEGER_TYPES),
    base_type=st.sampled_from(INTEGER_TYPES),
)
def test_integral_families_match_exact_causal_row_geometry(
    n: int,
    raw_k: int,
    raw_base: int,
    default: bool,
    n_type: Any,
    k_type: Any,
    base_type: Any,
) -> None:
    k = min(raw_k, n - 1)
    fold = n // (k + 1)
    last_valid_base = n - 1 - (k - 1) * fold
    base = fold if default else raw_base % last_valid_base + 1
    with np.errstate(all="raise"):
        splits = walk_forward_splits(n_type(n), k_type(k), None if default else base_type(base))
    assert len(splits) == k
    for i, (train, test) in enumerate(splits):
        start = base + i * fold
        end = n if i == k - 1 else start + fold
        assert train.tolist() == list(range(start))
        assert test.tolist() == list(range(start, end))
        assert int(train[-1]) < int(test[0])
        assert train.dtype == test.dtype == np.dtype(np.intp)
