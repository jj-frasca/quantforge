"""PBO via CSCV: result in [0,1], random configs average ~0.5 over many draws (the headline calibration), a dominant config gives low PBO, invalid inputs raise."""

import numpy as np
import numpy.typing as npt
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.pbo import probability_of_backtest_overfitting


def test_pbo_is_in_unit_interval() -> None:
    rng = np.random.default_rng(0)
    perf = rng.normal(0, 1, (240, 8))
    pbo = probability_of_backtest_overfitting(perf, n_splits=8)
    assert 0.0 <= pbo <= 1.0


def test_random_configurations_give_pbo_near_half_on_average() -> None:
    # The headline calibration: noise has no real edge -> ~50% overfit. A single CSCV draw is
    # high-variance (the C(10,5) splits are correlated), so the invariant is on the MEAN.
    pbos = [
        probability_of_backtest_overfitting(
            np.random.default_rng(seed).normal(0, 1, (300, 10)), n_splits=10
        )
        for seed in range(30)
    ]
    assert 0.4 <= float(np.mean(pbos)) <= 0.6


def test_dominant_configuration_gives_low_pbo() -> None:
    rng = np.random.default_rng(3)
    perf = rng.normal(0, 1, (300, 8))
    perf[:, 0] += 0.5  # config 0 has a genuine, persistent edge
    pbo = probability_of_backtest_overfitting(perf, n_splits=8)
    assert pbo < 0.2


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError, match="config"):
        probability_of_backtest_overfitting(np.zeros((100, 1)), n_splits=8)
    with pytest.raises(ValueError, match="even"):
        probability_of_backtest_overfitting(np.zeros((100, 4)), n_splits=7)
    with pytest.raises(ValueError, match="observations"):
        probability_of_backtest_overfitting(np.zeros((4, 4)), n_splits=8)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_returns_are_rejected_instead_of_scored_as_zero(bad: float) -> None:
    """ADR-106: invalid evidence cannot be converted into a finite, gate-changing rank."""
    performance = np.random.default_rng(3).normal(0.0, 1.0, (300, 8))
    performance[:, 0] += 0.5
    performance[0, 0] = bad

    with pytest.raises(ValueError, match="finite"):
        probability_of_backtest_overfitting(performance, n_splits=8)


@pytest.mark.parametrize("shape", [(8,), (4, 4, 2)])
def test_performance_must_be_a_two_dimensional_matrix(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        probability_of_backtest_overfitting(np.zeros(shape), n_splits=2)


def test_each_balanced_half_must_have_two_observations_for_sample_sharpe() -> None:
    with pytest.raises(ValueError, match="two observations"):
        probability_of_backtest_overfitting(np.zeros((2, 2)), n_splits=2)


# --- the group-sum formulation must be the same statistic, not merely a similar one ---


def _reference_pbo(performance: npt.NDArray[np.float64], n_splits: int) -> float:
    """PBO computed the direct way — slice the rows of each split and take mean/std on the slice.

    This is the definition Bailey et al. (2015) state and the implementation this module used
    before it precomputed group moments. It is kept as the oracle: an optimisation of a published
    statistic has to reproduce it exactly, not approximately.
    """
    from itertools import combinations

    n_obs, n_configs = performance.shape
    groups = np.array_split(np.arange(n_obs), n_splits)
    half = n_splits // 2
    overfit = 0
    total = 0
    for is_groups in combinations(range(n_splits), half):
        is_set = set(is_groups)
        is_rows = np.concatenate([groups[g] for g in is_groups])
        oos_rows = np.concatenate([groups[g] for g in range(n_splits) if g not in is_set])

        def sharpe(block: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
            mean = block.mean(axis=0)
            std = block.std(axis=0, ddof=1)
            return np.divide(mean, std, out=np.zeros_like(mean), where=std > 0)

        best = int(np.argmax(sharpe(performance[is_rows])))
        oos = sharpe(performance[oos_rows])
        rank = int(np.argsort(np.argsort(oos))[best])
        w = (rank + 1) / (n_configs + 1)
        overfit += int(np.log(w / (1.0 - w)) <= 0.0)
        total += 1
    return overfit / total


@pytest.mark.parametrize("seed", range(12))
def test_matches_the_direct_row_slicing_definition(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n_obs = int(rng.integers(40, 900))
    n_configs = int(rng.integers(2, 25))
    performance = rng.normal(0.0004, 0.011, (n_obs, n_configs))

    assert probability_of_backtest_overfitting(performance, 10) == pytest.approx(
        _reference_pbo(performance, 10)
    )


def test_a_config_that_never_moves_is_ranked_as_the_definition_ranks_it() -> None:
    """A zero-variance column gets Sharpe 0 by the `where=std > 0` guard, and the group-sum form
    must reproduce that rather than divide by a tiny accumulated variance."""
    rng = np.random.default_rng(3)
    performance = np.column_stack(
        [rng.normal(0.0004, 0.011, 300), np.zeros(300), np.full(300, 0.001)]
    )

    assert probability_of_backtest_overfitting(performance, 10) == pytest.approx(
        _reference_pbo(performance, 10)
    )


def test_an_uneven_split_still_matches_the_definition() -> None:
    """`np.array_split` leaves the last groups one row shorter when n_obs % n_splits != 0, so the
    group weights are not equal and a mean of group means would be wrong."""
    rng = np.random.default_rng(9)
    performance = rng.normal(0.0004, 0.011, (307, 6))

    assert probability_of_backtest_overfitting(performance, 10) == pytest.approx(
        _reference_pbo(performance, 10)
    )


def test_tied_candidates_cannot_move_pbo_across_the_gate_when_reordered() -> None:
    """ADR-105: column position is not evidence about overfitting.

    Positional argmax/argsort tie handling gave this same candidate set PBO 1/3 in its original
    order and 1/2 after a permutation, changing the strict production gate verdict.
    """
    performance = np.array(
        [
            [1.0, 0.0, 0.0, -1.0],
            [-1.0, -1.0, -1.0, -1.0],
            [-1.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0],
            [-1.0, 1.0, 1.0, -1.0],
            [0.0, 1.0, 0.0, -1.0],
            [1.0, 1.0, 1.0, -1.0],
        ],
        dtype=np.float64,
    )

    baseline = probability_of_backtest_overfitting(performance, n_splits=4)
    reordered = probability_of_backtest_overfitting(performance[:, [0, 3, 2, 1]], n_splits=4)

    assert baseline == pytest.approx(reordered)


@given(seed=st.integers(min_value=0, max_value=100_000))
def test_pbo_is_invariant_to_candidate_column_permutations(seed: int) -> None:
    """Financial-math invariant: relabeling a discrete candidate set cannot change PBO."""
    rng = np.random.default_rng(seed)
    performance = rng.choice([-1.0, 0.0, 1.0], size=(40, 6))
    permutation = rng.permutation(performance.shape[1])

    assert probability_of_backtest_overfitting(performance, n_splits=4) == pytest.approx(
        probability_of_backtest_overfitting(performance[:, permutation], n_splits=4)
    )
