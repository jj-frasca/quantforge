"""Deflated Sharpe: no haircut at n_trials==1, more trials deflate more, invalid params; Hypothesis invariant that DSR ≤ observed Sharpe."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.deflated_sharpe import deflated_sharpe


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
