"""Deflated Sharpe: no haircut at n_trials==1, more trials deflate more, invalid params; Hypothesis invariant that DSR ≤ observed Sharpe."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.stats import norm

from app.validation.deflated_sharpe import (
    deflated_sharpe,
    deflated_sharpe_probability,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    robust_sharpe_dispersion,
)


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


# --- ADR-054: the paper's statistic, which is a probability, not a Sharpe ---


def test_psr_is_one_half_when_the_observed_sharpe_equals_the_benchmark() -> None:
    """PSR is the probability that the true Sharpe exceeds the benchmark. At equality the
    standardized excess is zero and the Normal CDF is 0.5, whatever the sample or its shape."""
    assert probabilistic_sharpe_ratio(
        1.2, benchmark_sr=1.2, n_returns=500, skew=-0.4, kurtosis=6.0
    ) == pytest.approx(0.5)


def test_psr_reduces_to_lo_s_normal_standard_error_on_a_normal_series() -> None:
    """Zero skew and RAW kurtosis 3 must leave exactly Lo (2002)'s sqrt((1 + SR^2/2)/(n-1)). All
    Sharpes here are PER-PERIOD, as the docstring requires: an annualized value saturates the CDF
    and the test would pass without testing anything."""
    observed, benchmark, n = 0.10, 0.03, 401
    expected = float(
        norm.cdf((observed - benchmark) / math.sqrt((1 + 0.5 * observed**2) / (n - 1)))
    )
    assert probabilistic_sharpe_ratio(
        observed, benchmark_sr=benchmark, n_returns=n, skew=0.0, kurtosis=3.0
    ) == pytest.approx(expected)


def test_psr_rejects_the_excess_kurtosis_convention_outright() -> None:
    """Passing excess kurtosis (0.0 for a Normal series) drives kurtosis - skew^2 - 1 negative, so
    the mix-up raises rather than quietly reporting a smaller standard error."""
    with pytest.raises(ValueError, match="variance"):
        probabilistic_sharpe_ratio(0.10, benchmark_sr=0.03, n_returns=401, skew=0.0, kurtosis=0.0)


def test_psr_falls_when_the_returns_are_more_negatively_skewed() -> None:
    """Negative skew and fat tails make the same Sharpe less trustworthy — the whole reason the
    paper's correction exists, and precisely what the margin form omits."""
    normal = probabilistic_sharpe_ratio(
        0.10, benchmark_sr=0.03, n_returns=500, skew=0.0, kurtosis=3.0
    )
    skewed = probabilistic_sharpe_ratio(
        0.10, benchmark_sr=0.03, n_returns=500, skew=-1.5, kurtosis=9.0
    )
    assert skewed < normal


def test_psr_rises_with_a_longer_track_record() -> None:
    short = probabilistic_sharpe_ratio(
        0.10, benchmark_sr=0.03, n_returns=250, skew=0.0, kurtosis=3.0
    )
    long = probabilistic_sharpe_ratio(
        0.10, benchmark_sr=0.03, n_returns=2500, skew=0.0, kurtosis=3.0
    )
    assert long > short


def test_psr_needs_at_least_two_returns() -> None:
    with pytest.raises(ValueError, match="n_returns"):
        probabilistic_sharpe_ratio(1.5, benchmark_sr=0.5, n_returns=1, skew=0.0, kurtosis=3.0)


def test_psr_rejects_a_degenerate_variance() -> None:
    """kurtosis - skew^2 - 1 is the variance of the Sharpe estimator; a combination that drives it
    to zero or below is not a distribution and must not silently return 1.0."""
    with pytest.raises(ValueError, match="variance"):
        probabilistic_sharpe_ratio(1.5, benchmark_sr=0.5, n_returns=500, skew=0.0, kurtosis=0.5)


def test_deflated_sharpe_probability_prices_the_trials_it_was_selected_from() -> None:
    """The paper's DSR is PSR against the multiple-testing-adjusted threshold, so more trials at
    the same observed Sharpe must lower it."""
    few = deflated_sharpe_probability(
        0.12, n_trials=5, sr_std=0.03, n_returns=1000, skew=0.0, kurtosis=3.0
    )
    many = deflated_sharpe_probability(
        0.12, n_trials=500, sr_std=0.03, n_returns=1000, skew=0.0, kurtosis=3.0
    )
    assert 0.0 <= many < few <= 1.0


def test_deflated_sharpe_probability_agrees_with_psr_at_the_same_benchmark() -> None:
    """The two must be the same function of the haircut — a separate implementation would drift."""
    haircut = expected_max_sharpe(200, 0.03)
    assert deflated_sharpe_probability(
        0.12, n_trials=200, sr_std=0.03, n_returns=1000, skew=0.0, kurtosis=3.0
    ) == pytest.approx(
        probabilistic_sharpe_ratio(
            0.12, benchmark_sr=haircut, n_returns=1000, skew=0.0, kurtosis=3.0
        )
    )


@given(
    observed=st.floats(min_value=-0.5, max_value=0.5),
    n_trials=st.integers(min_value=1, max_value=5000),
    n_returns=st.integers(min_value=30, max_value=10_000),
)
def test_the_probability_form_is_always_a_probability(
    observed: float, n_trials: int, n_returns: int
) -> None:
    """The margin form's invariant is DSR <= observed Sharpe; the probability form's is [0, 1].
    Confusing the two is exactly what FINDING-007 is about."""
    value = deflated_sharpe_probability(
        observed, n_trials=n_trials, sr_std=0.03, n_returns=n_returns, skew=0.0, kurtosis=3.0
    )
    assert 0.0 <= value <= 1.0
