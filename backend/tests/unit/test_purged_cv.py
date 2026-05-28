import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.purged_cv import purged_kfold_splits


def test_returns_requested_folds_and_covers_all_indices() -> None:
    splits = purged_kfold_splits(n_obs=100, n_splits=5, embargo=0)
    assert len(splits) == 5
    tested = np.concatenate([test for _, test in splits])
    assert sorted(tested.tolist()) == list(range(100))  # each index tested exactly once


def test_embargo_removes_neighbours_from_train() -> None:
    embargo = 3
    for train_idx, test_idx in purged_kfold_splits(n_obs=100, n_splits=5, embargo=embargo):
        lo = int(test_idx.min()) - embargo
        hi = int(test_idx.max()) + embargo
        assert not ((train_idx >= lo) & (train_idx <= hi)).any()


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        purged_kfold_splits(n_obs=100, n_splits=1)
    with pytest.raises(ValueError):
        purged_kfold_splits(n_obs=100, n_splits=5, embargo=-1)
    with pytest.raises(ValueError):
        purged_kfold_splits(n_obs=3, n_splits=5)


@given(
    n_obs=st.integers(min_value=20, max_value=300),
    n_splits=st.integers(min_value=2, max_value=8),
    embargo=st.integers(min_value=0, max_value=10),
)
def test_no_train_index_within_embargo_of_test(n_obs: int, n_splits: int, embargo: int) -> None:
    # validation invariant: purged CV embargo removes overlapping samples (no leakage).
    for train_idx, test_idx in purged_kfold_splits(n_obs, n_splits, embargo):
        if len(train_idx) == 0:
            continue
        t_min, t_max = int(test_idx.min()), int(test_idx.max())
        for t in train_idx.tolist():
            assert t < t_min - embargo or t > t_max + embargo
