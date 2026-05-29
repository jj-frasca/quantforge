"""MonteCarloSimulator (GBM): output shape, first column == s0, deterministic per seed, zero-vol drift, invalid params; Hypothesis invariant that paths are always positive."""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.simulation.monte_carlo import MonteCarloSimulator


def test_simulate_returns_expected_shape() -> None:
    paths = MonteCarloSimulator().simulate(
        s0=100.0, mu=0.05, sigma=0.2, n_steps=50, n_paths=10, seed=1
    )
    assert paths.shape == (10, 51)  # n_steps + 1 (includes s0)


def test_first_column_is_initial_price() -> None:
    paths = MonteCarloSimulator().simulate(
        s0=100.0, mu=0.05, sigma=0.2, n_steps=20, n_paths=5, seed=1
    )
    assert np.allclose(paths[:, 0], 100.0)


def test_paths_are_strictly_positive() -> None:
    paths = MonteCarloSimulator().simulate(
        s0=100.0, mu=0.1, sigma=0.5, n_steps=252, n_paths=100, seed=7
    )
    assert (paths > 0).all()


def test_same_seed_is_deterministic() -> None:
    a = MonteCarloSimulator().simulate(s0=100.0, mu=0.05, sigma=0.2, n_steps=30, n_paths=8, seed=42)
    b = MonteCarloSimulator().simulate(s0=100.0, mu=0.05, sigma=0.2, n_steps=30, n_paths=8, seed=42)
    assert np.array_equal(a, b)


def test_zero_volatility_is_deterministic_drift() -> None:
    paths = MonteCarloSimulator().simulate(
        s0=100.0, mu=0.05, sigma=0.0, n_steps=10, n_paths=4, seed=1
    )
    # all paths identical with no volatility
    assert np.allclose(paths, paths[0])


def test_invalid_params_raise() -> None:
    sim = MonteCarloSimulator()
    with pytest.raises(ValueError):
        sim.simulate(s0=0.0, mu=0.05, sigma=0.2, n_steps=10, n_paths=5)
    with pytest.raises(ValueError):
        sim.simulate(s0=100.0, mu=0.05, sigma=-0.1, n_steps=10, n_paths=5)
    with pytest.raises(ValueError):
        sim.simulate(s0=100.0, mu=0.05, sigma=0.2, n_steps=0, n_paths=5)
    with pytest.raises(ValueError):
        sim.simulate(s0=100.0, mu=0.05, sigma=0.2, n_steps=10, n_paths=0)


@given(
    mu=st.floats(min_value=-1.0, max_value=1.0),
    sigma=st.floats(min_value=0.0, max_value=2.0),
    seed=st.integers(min_value=0, max_value=10_000),
)
def test_gbm_paths_always_positive(mu: float, sigma: float, seed: int) -> None:
    # §8 invariant #8: GBM Monte Carlo paths are always positive.
    paths = MonteCarloSimulator().simulate(
        s0=50.0, mu=mu, sigma=sigma, n_steps=40, n_paths=20, seed=seed
    )
    assert np.isfinite(paths).all()
    assert (paths > 0).all()
