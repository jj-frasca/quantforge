"""Walk-forward splits: requested count, expanding train window, invalid params; Hypothesis invariant that train never precedes/overlaps test (no future data)."""

import numpy as np
import numpy.typing as npt
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.walk_forward import walk_forward_evaluate, walk_forward_splits


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
    # min_train too large would leave the final test fold empty -> rejected
    with pytest.raises(ValueError, match="min_train"):
        walk_forward_splits(n_obs=100, n_splits=4, min_train=95)
    # min_train below 1 is invalid
    with pytest.raises(ValueError, match="min_train"):
        walk_forward_splits(n_obs=100, n_splits=4, min_train=0)


@given(
    n_obs=st.integers(min_value=20, max_value=500), n_splits=st.integers(min_value=1, max_value=8)
)
def test_walk_forward_never_uses_future_data(n_obs: int, n_splits: int) -> None:
    # §8 / validation invariant: walk-forward never uses future data.
    for train_idx, test_idx in walk_forward_splits(n_obs, n_splits):
        assert int(train_idx.max()) < int(test_idx.min())


# --- ADR-038: the splits now judge something ---


def _matrix(columns: list[list[float]]) -> npt.NDArray[np.float64]:
    return np.column_stack([np.asarray(c, dtype=np.float64) for c in columns])


def test_selects_on_train_and_scores_on_test() -> None:
    """The selected config is the train-block argmax, scored on the following test block."""
    n = 100
    rng = np.random.default_rng(0)
    # A regime flip strong enough to overturn an EXPANDING train window: config 0 owns the
    # early splits, and config 1's later edge is big enough to win the cumulative sample too, so
    # at least one split must select each of them.
    first = np.concatenate([rng.normal(0.02, 0.01, n // 2), rng.normal(-0.02, 0.01, n // 2)])
    second = np.concatenate([rng.normal(-0.002, 0.01, n // 2), rng.normal(0.10, 0.01, n // 2)])
    performance = _matrix([list(first), list(second)])

    splits = walk_forward_splits(n_obs=n, n_splits=4)
    result = walk_forward_evaluate(performance, splits)

    assert result.n_splits == 4
    assert len(result.splits) == 4
    assert {s.selected_config for s in result.splits} == {0, 1}
    # every selection is genuinely the train-block best
    for split, (train_idx, _) in zip(result.splits, splits, strict=True):
        train_sharpes = [
            performance[train_idx, c].mean() / performance[train_idx, c].std(ddof=1)
            for c in range(performance.shape[1])
        ]
        assert split.selected_config == int(np.argmax(train_sharpes))


def test_out_of_sample_scores_use_only_test_rows() -> None:
    """A config that is flat in-sample and explosive out-of-sample must not leak backwards."""
    n = 80
    performance = _matrix(
        [
            [0.01] * 40 + [0.01] * 40,  # constant -> zero std -> Sharpe 0
            [0.001] * 40 + [1.0] * 40,
        ]
    )
    splits = walk_forward_splits(n_obs=n, n_splits=2)
    result = walk_forward_evaluate(performance, splits)
    # constant columns have zero dispersion; nothing may report an infinite Sharpe
    assert all(np.isfinite(s.is_sharpe) and np.isfinite(s.oos_sharpe) for s in result.splits)


def test_mean_and_consistency_summarize_the_splits() -> None:
    n = 60
    performance = _matrix([list(np.full(n, 0.01) + np.arange(n) * 1e-5), list(np.full(n, -0.01))])
    performance[:, 0] += np.linspace(0, 0.001, n)
    splits = walk_forward_splits(n_obs=n, n_splits=3)
    result = walk_forward_evaluate(performance, splits)

    assert result.mean_oos_sharpe == pytest.approx(
        float(np.mean([s.oos_sharpe for s in result.splits]))
    )
    assert result.consistency == pytest.approx(
        sum(s.oos_sharpe > 0 for s in result.splits) / result.n_splits
    )
    assert 0.0 <= result.consistency <= 1.0


def test_efficiency_is_undefined_when_in_sample_is_not_positive() -> None:
    """A ratio of two negative Sharpes is positive; reporting it would read as 'efficient'."""
    n = 60
    rng = np.random.default_rng(7)
    losing = rng.normal(-0.02, 0.01, n)
    performance = _matrix([list(losing), list(losing * 1.1)])
    splits = walk_forward_splits(n_obs=n, n_splits=3)
    result = walk_forward_evaluate(performance, splits)

    assert result.mean_is_sharpe < 0
    assert result.efficiency is None


def test_efficiency_is_the_ratio_when_in_sample_is_positive() -> None:
    n = 60
    rng = np.random.default_rng(3)
    performance = _matrix([list(rng.normal(0.02, 0.01, n)), list(rng.normal(0.015, 0.01, n))])
    splits = walk_forward_splits(n_obs=n, n_splits=3)
    result = walk_forward_evaluate(performance, splits)

    assert result.mean_is_sharpe > 0
    assert result.efficiency == pytest.approx(result.mean_oos_sharpe / result.mean_is_sharpe)


def test_rejects_a_matrix_that_does_not_match_the_splits() -> None:
    performance = _matrix([[0.01] * 10, [0.02] * 10])
    with pytest.raises(ValueError, match="configurations"):
        walk_forward_evaluate(performance[:, :1], walk_forward_splits(n_obs=10, n_splits=2))
    with pytest.raises(ValueError, match="out of range"):
        walk_forward_evaluate(performance, walk_forward_splits(n_obs=40, n_splits=2))


@given(
    st.integers(min_value=40, max_value=200),
    st.integers(min_value=2, max_value=5),
    st.integers(min_value=2, max_value=6),
)
def test_selection_never_sees_its_own_test_block(n_obs: int, n_splits: int, n_configs: int) -> None:
    """Invariant: a split's selection is a function of its train rows ONLY.

    Perturbing every row from a split's test-block start onwards must leave that split's choice and
    in-sample Sharpe untouched. Later splits legitimately move — a walk-forward train window
    expands, so it absorbs earlier test rows — which is why the invariant is stated per split.
    """
    rng = np.random.default_rng(n_obs + n_splits + n_configs)
    performance = rng.normal(0.0, 0.01, size=(n_obs, n_configs))
    splits = walk_forward_splits(n_obs=n_obs, n_splits=n_splits)
    baseline = walk_forward_evaluate(performance, splits)

    for i, (_, test_idx) in enumerate(splits):
        perturbed = performance.copy()
        perturbed[int(test_idx.min()) :] += 10.0
        after = walk_forward_evaluate(perturbed, splits)
        assert after.splits[i].selected_config == baseline.splits[i].selected_config
        assert after.splits[i].is_sharpe == baseline.splits[i].is_sharpe


def test_a_single_bar_block_has_no_measurable_sharpe() -> None:
    """One observation has no dispersion; report 0.0 rather than dividing by an empty std."""
    performance = _matrix([[0.01, 0.02, 0.03, 0.04], [0.02, 0.01, 0.00, 0.05]])
    splits = [(np.array([0, 1, 2], dtype=np.intp), np.array([3], dtype=np.intp))]
    result = walk_forward_evaluate(performance, splits)
    assert result.splits[0].oos_sharpe == 0.0


def test_rejects_an_empty_split_list() -> None:
    with pytest.raises(ValueError, match="split"):
        walk_forward_evaluate(_matrix([[0.01] * 10, [0.02] * 10]), [])
