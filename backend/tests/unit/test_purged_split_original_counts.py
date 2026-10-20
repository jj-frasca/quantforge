"""ADR-330: original split counts cannot wrap an embargo into overlapping rows."""

from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.purged_cv import purged_kfold_splits

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


@pytest.mark.parametrize(
    "args",
    [
        (8, 2, np.uint32(2)),
        (8, 2, np.uint64(2)),
        (np.uint8(8), 2, 10),
        (8, np.uint8(2), 10),
        (np.uint8(8), np.uint8(2), 10),
    ],
)
def test_unsigned_witnesses_exclude_the_entire_embargo(args: tuple[Any, Any, Any]) -> None:
    n, k, gap = map(int, args)
    with np.errstate(over="ignore"):
        folds = purged_kfold_splits(*args)
    for train, test in folds:
        expected = [i for i in range(n) if i < int(test[0]) - gap or i > int(test[-1]) + gap]
        assert train.tolist() == expected
    assert len(folds) == k


@pytest.mark.parametrize("parameter", ["n_obs", "n_splits", "embargo"])
@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        np.bool_(True),
        8.0,
        np.float64(8),
        Fraction(8, 1),
        "8",
        8 + 0j,
        None,
        [8],
        np.array(8),
        np.array([8]),
        float("nan"),
        float("inf"),
        -1,
        np.int64(-1),
    ],
)
def test_original_noncounts_refuse_before_geometry(parameter: str, bad: Any) -> None:
    args = {"n_obs": 8, "n_splits": 2, "embargo": 0}
    args[parameter] = bad
    with pytest.raises(ValueError, match=parameter):
        purged_kfold_splits(**args)


@pytest.mark.parametrize("dtype", INTEGER_TYPES)
def test_huge_embargo_purges_every_training_row(dtype: Any) -> None:
    gap = 10**100 if dtype is int else dtype(np.iinfo(dtype).max)
    with np.errstate(all="raise"):
        folds = purged_kfold_splits(8, 2, gap)
    assert all(train.size == 0 for train, _ in folds)
    assert np.concatenate([test for _, test in folds]).tolist() == list(range(8))


@pytest.mark.parametrize(
    "args,message",
    [
        ((-1, 1, -1), "n_splits must be >= 2"),
        ((-1, 2, -1), "embargo"),
        ((-1, 2, 0), "n_obs"),
        ((0, 2, 0), "n_obs must be >= n_splits"),
        ((8, 0, 0), "n_splits must be >= 2"),
        ((8, 1, 0), "n_splits must be >= 2"),
    ],
)
def test_existing_geometry_check_precedence(args: tuple[int, int, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        purged_kfold_splits(*args)


@given(
    n=st.integers(2, 60),
    raw_k=st.integers(2, 60),
    gap=st.integers(0, 127),
    n_type=st.sampled_from(INTEGER_TYPES),
    k_type=st.sampled_from(INTEGER_TYPES),
    gap_type=st.sampled_from(INTEGER_TYPES),
)
def test_integral_families_match_exact_set_geometry(
    n: int,
    raw_k: int,
    gap: int,
    n_type: Any,
    k_type: Any,
    gap_type: Any,
) -> None:
    k = min(n, raw_k)
    with np.errstate(all="raise"):
        folds = purged_kfold_splits(n_type(n), k_type(k), gap_type(gap))
    tested: list[int] = []
    start = 0
    for j, (train, test) in enumerate(folds):
        size = n // k + int(j < n % k)
        expected_test = list(range(start, start + size))
        expected_train = [i for i in range(n) if all(abs(i - t) > gap for t in expected_test)]
        assert test.tolist() == expected_test
        assert train.tolist() == expected_train
        assert train.dtype == test.dtype == np.dtype(np.intp)
        tested.extend(test.tolist())
        start += size
    assert len(folds) == k
    assert tested == list(range(n))
