import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.walk_forward import walk_forward_splits


def test_returns_requested_number_of_splits() -> None:
    splits = walk_forward_splits(n_obs=100, n_splits=4)
    assert len(splits) == 4


def test_train_never_overlaps_or_precedes_test() -> None:
    for train_idx, test_idx in walk_forward_splits(n_obs=100, n_splits=4):
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        assert int(train_idx.max()) < int(test_idx.min())  # no future data


def test_training_window_expands() -> None:
    splits = walk_forward_splits(n_obs=100, n_splits=4)
    sizes = [len(train) for train, _ in splits]
    assert sizes == sorted(sizes)
    assert sizes[0] < sizes[-1]


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        walk_forward_splits(n_obs=100, n_splits=0)
    with pytest.raises(ValueError):
        walk_forward_splits(n_obs=2, n_splits=5)


@given(
    n_obs=st.integers(min_value=20, max_value=500), n_splits=st.integers(min_value=1, max_value=8)
)
def test_walk_forward_never_uses_future_data(n_obs: int, n_splits: int) -> None:
    # §8 / validation invariant: walk-forward never uses future data.
    for train_idx, test_idx in walk_forward_splits(n_obs, n_splits):
        assert int(train_idx.max()) < int(test_idx.min())
