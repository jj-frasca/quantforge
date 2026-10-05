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


def test_paths_are_strictly_positive_under_extreme_volatility() -> None:
    # FINDING-051/ADR-123: the class's own invariant claim ("every factor is exp(...) > 0, so all
    # path values are strictly positive") is true in exact arithmetic but not in float64 — a
    # sufficiently extreme (if unrealistic) sigma drives the TRUE compounded GBM value below
    # float64's smallest representable double for a real fraction of paths, and a naive cumprod
    # floors those entries to exactly 0.0. sigma=40 (4000% annualized vol) at a 1-year horizon
    # reproduces this directly against the pre-fix implementation.
    paths = MonteCarloSimulator().simulate(
        s0=100.0, mu=0.0, sigma=40.0, n_steps=252, n_paths=500, seed=1
    )
    assert np.isfinite(paths).all()
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


@pytest.mark.parametrize("name", ["s0", "mu", "sigma", "dt"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_simulation_rejects_nonfinite_parameters(name: str, value: float) -> None:
    parameters = {"s0": 100.0, "mu": 0.05, "sigma": 0.2, "dt": 1 / 252}
    parameters[name] = value
    with pytest.raises(ValueError, match="finite"):
        MonteCarloSimulator().simulate(**parameters, n_steps=2, n_paths=1, seed=1)


@pytest.mark.parametrize("dt", [0.0, -1.0])
def test_simulation_rejects_nonpositive_time_increment(dt: float) -> None:
    with pytest.raises(ValueError, match="dt"):
        MonteCarloSimulator().simulate(s0=100, mu=0.05, sigma=0.2, dt=dt, n_steps=2, n_paths=1)


@pytest.mark.parametrize("mu,sigma", [(100_000.0, 0.0), (0.0, 1e300)])
def test_simulation_rejects_nonrepresentable_arithmetic(mu: float, sigma: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        MonteCarloSimulator().simulate(s0=100, mu=mu, sigma=sigma, n_steps=2, n_paths=1, seed=1)


def test_simulation_preserves_subnormal_initial_and_flat_path() -> None:
    paths = MonteCarloSimulator().simulate(s0=1e-320, mu=0, sigma=0, n_steps=2, n_paths=2, seed=1)
    assert np.all(paths == 1e-320)


def test_simulation_underflow_uses_smallest_positive_subnormal_floor() -> None:
    paths = MonteCarloSimulator().simulate(
        s0=1, mu=-1_000_000, sigma=0, n_steps=2, n_paths=1, seed=1
    )
    assert paths[0, 0] == 1
    assert np.all(paths[:, 1:] == float.fromhex("0x0.0000000000001p-1022"))


def test_simulation_rejects_overflowed_numpy_scalar_drift_under_strict_error_mode() -> None:
    with np.errstate(all="raise"), pytest.raises(ValueError, match="finite"):
        MonteCarloSimulator().simulate(s0=1, mu=0, sigma=np.float64(1e300), n_steps=2, n_paths=1)


def test_simulation_rejects_finite_parameter_drift_product_overflow() -> None:
    with pytest.raises(ValueError, match="finite"):
        MonteCarloSimulator().simulate(s0=1, mu=1e308, sigma=0, dt=1e308, n_steps=2, n_paths=1)


@given(s0=st.floats(min_value=1e-320, max_value=1e-309, allow_nan=False, allow_infinity=False))
def test_simulation_flat_subnormal_paths_preserve_price_scale(s0: float) -> None:
    paths = MonteCarloSimulator().simulate(s0=s0, mu=0, sigma=0, n_steps=3, n_paths=2, seed=1)
    assert np.all(paths == s0)
