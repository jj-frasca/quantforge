"""Deflated Sharpe: no haircut at n_trials==1, more trials deflate more, invalid params; Hypothesis invariant that DSR ≤ observed Sharpe."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.deflated_sharpe import deflated_sharpe, robust_sharpe_dispersion


def test_robust_dispersion_matches_normal_interquartile_scale() -> None:
    normal_quartile = 0.6744897501960817
    sharpes = [-2.0, -normal_quartile, 0.0, normal_quartile, 2.0]
    assert robust_sharpe_dispersion(sharpes) == pytest.approx(1.0)


def test_robust_dispersion_resists_a_signal_contaminated_tail() -> None:
    baseline = [-1.0, -0.5, 0.0, 0.5, 1.0]
    contaminated = [-1.0, -0.5, 0.0, 0.5, 100.0]
    assert robust_sharpe_dispersion(contaminated) == pytest.approx(
        robust_sharpe_dispersion(baseline)
    )


def test_robust_dispersion_rejects_too_few_or_non_finite_sharpes() -> None:
    with pytest.raises(ValueError, match="at least two"):
        robust_sharpe_dispersion([0.0])
    with pytest.raises(ValueError, match="finite"):
        robust_sharpe_dispersion([0.0, float("nan")])


def test_robust_dispersion_keeps_sample_std_for_tiny_families() -> None:
    assert robust_sharpe_dispersion([-1.0, 1.0]) == pytest.approx(2.0**0.5)


@given(
    sharpes=st.lists(
        st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=4,
        max_size=100,
    )
)
def test_robust_dispersion_is_order_invariant(sharpes: list[float]) -> None:
    assert robust_sharpe_dispersion(sharpes) == pytest.approx(
        robust_sharpe_dispersion(list(reversed(sharpes)))
    )


def test_single_trial_has_no_haircut() -> None:
    assert deflated_sharpe(observed_sr=1.5, n_trials=1, sr_std=1.0) == pytest.approx(1.5)


def test_more_trials_deflate_more() -> None:
    few = deflated_sharpe(observed_sr=2.0, n_trials=5, sr_std=1.0)
    many = deflated_sharpe(observed_sr=2.0, n_trials=500, sr_std=1.0)
    assert many <= few <= 2.0


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError, match="n_trials"):
        deflated_sharpe(observed_sr=1.0, n_trials=0, sr_std=1.0)
    with pytest.raises(ValueError, match="sr_std"):
        deflated_sharpe(observed_sr=1.0, n_trials=10, sr_std=0.0)


@given(
    observed=st.floats(min_value=-3.0, max_value=3.0),
    n_trials=st.integers(min_value=1, max_value=2000),
    sr_std=st.floats(min_value=0.01, max_value=2.0),
)
def test_deflated_never_exceeds_observed(observed: float, n_trials: int, sr_std: float) -> None:
    # §8 invariant #5: Deflated Sharpe <= observed Sharpe.
    assert deflated_sharpe(observed, n_trials, sr_std) <= observed + 1e-9
