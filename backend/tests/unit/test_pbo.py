import numpy as np
import pytest

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
