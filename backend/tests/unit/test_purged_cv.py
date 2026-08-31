"""Purged K-fold CV: folds partition all indices once, embargo removes neighbours, invalid params; Hypothesis invariant that no train index lies within the embargo of any test index."""

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.backtesting.metrics import sharpe_ratio
from app.research.strategies.sma import SMAStrategy
from app.validation.purged_cv import (
    lookback_embargo,
    purged_cv_evaluate,
    purged_kfold_splits,
)


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


# --- ADR-039: the folds now judge something, and the embargo is sized from the lookback ---


def _matrix(columns: list[list[float]]) -> npt.NDArray[np.float64]:
    return np.column_stack([np.asarray(c, dtype=np.float64) for c in columns])


def test_selects_on_the_purged_train_rows_and_scores_on_the_fold() -> None:
    n = 120
    rng = np.random.default_rng(0)
    performance = _matrix([list(rng.normal(0.02, 0.01, n)), list(rng.normal(-0.02, 0.01, n))])
    splits = purged_kfold_splits(n_obs=n, n_splits=4, embargo=3)
    result = purged_cv_evaluate(performance, splits, embargo=3)

    assert result.n_folds == 4
    assert result.embargo == 3
    assert all(f.selected_config == 0 for f in result.folds)  # config 0 dominates everywhere
    for fold, (train_idx, test_idx) in zip(result.folds, splits, strict=True):
        assert fold.n_train == len(train_idx)
        assert fold.n_test == len(test_idx)


def test_reports_dispersion_not_just_a_mean() -> None:
    """A mean over folds with no dispersion is exactly the statistic this project criticizes."""
    n = 120
    rng = np.random.default_rng(4)
    performance = _matrix([list(rng.normal(0.0, 0.02, n)), list(rng.normal(0.0, 0.02, n))])
    splits = purged_kfold_splits(n_obs=n, n_splits=4, embargo=2)
    result = purged_cv_evaluate(performance, splits, embargo=2)

    assert result.oos_sharpe_std >= 0.0
    assert result.mean_oos_sharpe == pytest.approx(
        float(np.mean([f.oos_sharpe for f in result.folds]))
    )
    assert result.consistency == pytest.approx(
        sum(f.oos_sharpe > 0 for f in result.folds) / result.n_folds
    )


def test_purged_cv_sharpe_is_annualized() -> None:
    n = 120
    rng = np.random.default_rng(9)
    performance = _matrix([list(rng.normal(0.001, 0.01, n)), list(rng.normal(0.0, 0.01, n))])
    splits = purged_kfold_splits(n_obs=n, n_splits=3, embargo=2)
    result = purged_cv_evaluate(performance, splits, embargo=2)

    fold, (_, test_idx) = result.folds[0], splits[0]
    expected = sharpe_ratio(pd.Series(performance[test_idx, fold.selected_config]))
    assert fold.oos_sharpe == pytest.approx(expected)


def test_a_fold_with_no_surviving_train_rows_is_dropped() -> None:
    """A huge embargo can purge the entire training set; a fold with nothing to select on is not
    a measurement and must not be counted as one."""
    n = 40
    performance = _matrix([[0.01] * n, [0.02] * n])
    splits = [
        (np.array([], dtype=np.intp), np.arange(0, 20, dtype=np.intp)),
        (np.arange(0, 20, dtype=np.intp), np.arange(20, 40, dtype=np.intp)),
    ]
    result = purged_cv_evaluate(performance, splits, embargo=100)
    assert result.n_folds == 1


def test_rejects_a_matrix_or_split_set_it_cannot_evaluate() -> None:
    performance = _matrix([[0.01] * 20, [0.02] * 20])
    with pytest.raises(ValueError, match="configurations"):
        purged_cv_evaluate(performance[:, :1], purged_kfold_splits(20, 2), embargo=0)
    with pytest.raises(ValueError, match="fold"):
        purged_cv_evaluate(performance, [], embargo=0)
    with pytest.raises(ValueError, match="fold"):
        purged_cv_evaluate(
            performance,
            [(np.array([], dtype=np.intp), np.arange(0, 20, dtype=np.intp))],
            embargo=0,
        )


def test_embargo_is_the_longest_lookback_in_the_grid() -> None:
    configs = [SMAStrategy(fast=5, slow=20), SMAStrategy(fast=10, slow=200)]
    assert lookback_embargo(configs, floor=2) == 200


def test_embargo_never_falls_below_the_floor() -> None:
    configs = [SMAStrategy(fast=1, slow=2), SMAStrategy(fast=1, slow=3)]
    assert lookback_embargo(configs, floor=10) == 10


def test_a_negative_embargo_floor_is_rejected() -> None:
    with pytest.raises(ValueError, match="floor"):
        lookback_embargo([SMAStrategy(fast=5, slow=20)], floor=-1)


def test_a_single_bar_fold_has_no_measurable_sharpe() -> None:
    """One observation has no dispersion; report 0.0 rather than dividing by an empty std."""
    performance = _matrix([[0.01, 0.02, 0.03, 0.04], [0.02, 0.01, 0.00, 0.05]])
    splits = [(np.array([0, 1, 2], dtype=np.intp), np.array([3], dtype=np.intp))]
    result = purged_cv_evaluate(performance, splits, embargo=0)
    assert result.folds[0].oos_sharpe == 0.0
    assert result.oos_sharpe_std == 0.0  # ddof=1 on one fold would be NaN


# --- ADR-078: the same folds, scored on buy-and-hold ---


def test_the_benchmark_is_scored_on_the_same_folds() -> None:
    rng = np.random.default_rng(11)
    n = 400
    performance = _matrix([list(rng.normal(0.001, 0.01, n)) for _ in range(3)])
    hold = rng.normal(0.01, 0.008, n)
    splits = purged_kfold_splits(n, n_splits=5, embargo=3)

    result = purged_cv_evaluate(performance, splits, embargo=3, benchmark=hold)

    assert result.mean_oos_hold_sharpe == pytest.approx(
        float(np.mean([sharpe_ratio(pd.Series(hold[test_idx])) for _, test_idx in splits]))
    )


def test_an_unbenchmarked_purged_cv_reports_not_measured() -> None:
    """ADR-067: a missing benchmark is not a benchmark of zero."""
    performance = _matrix([[0.01] * 60, [0.02] * 60])
    splits = purged_kfold_splits(60, n_splits=3, embargo=0)

    assert purged_cv_evaluate(performance, splits, embargo=0).mean_oos_hold_sharpe is None


def test_a_benchmark_that_does_not_span_the_window_is_refused() -> None:
    performance = _matrix([[0.01] * 60, [0.02] * 60])
    splits = purged_kfold_splits(60, n_splits=3, embargo=0)

    with pytest.raises(ValueError, match="benchmark"):
        purged_cv_evaluate(performance, splits, embargo=0, benchmark=np.full(59, 0.01))


def test_the_benchmark_average_covers_only_the_folds_that_were_kept() -> None:
    """A fold purged away entirely is dropped (ADR-039), so averaging the benchmark over it would
    pair the strategy's score with blocks it was never scored on — the confound ADR-078 removes,
    reintroduced one fold at a time."""
    n = 40
    performance = _matrix([[0.01] * n, [0.02] * n])
    kept = np.arange(20, 40, dtype=np.intp)
    splits = [
        (np.array([], dtype=np.intp), np.arange(0, 20, dtype=np.intp)),
        (np.arange(0, 20, dtype=np.intp), kept),
    ]
    hold = np.concatenate([np.full(20, 0.05), np.linspace(0.001, 0.002, 20)])

    result = purged_cv_evaluate(performance, splits, embargo=100, benchmark=hold)

    assert result.n_folds == 1
    assert result.mean_oos_hold_sharpe == pytest.approx(sharpe_ratio(pd.Series(hold[kept])))


def test_holding_beats_a_strategy_that_only_scales_the_drift() -> None:
    """The point of the benchmark (ADR-078, following ADR-068): on a series whose whole return is
    drift, a finalist that merely scales it has a Sharpe equal to holding, and the EXCESS is zero.
    Purged CV's folds tile the whole window, so the control covers exactly the searched history."""
    rng = np.random.default_rng(5)
    n = 600
    hold = rng.normal(0.0008, 0.01, n)
    performance = _matrix([list(hold), list(hold * 0.5)])
    splits = purged_kfold_splits(n, n_splits=5, embargo=2)

    result = purged_cv_evaluate(performance, splits, embargo=2, benchmark=hold)

    assert result.mean_oos_hold_sharpe is not None
    assert result.mean_oos_sharpe - result.mean_oos_hold_sharpe == pytest.approx(0.0, abs=1e-9)
