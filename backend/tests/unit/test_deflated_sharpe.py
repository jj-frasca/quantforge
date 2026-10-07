"""Deflated Sharpe: no haircut at n_trials==1, more trials deflate more, invalid params; Hypothesis invariant that DSR ≤ observed Sharpe."""

import math
from functools import partial

import numpy as np
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
    """The retained strict moment-domain policy rejects nonpositive Pearson slack.

    This guard is distinct from the actual Sharpe-dependent standard-error factor (ADR-193).
    """
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


@pytest.fixture(
    params=[
        expected_max_sharpe,
        partial(deflated_sharpe, observed_sr=0.2),
        partial(
            deflated_sharpe_probability,
            observed_sr=0.2,
            n_returns=100,
            skew=0.0,
            kurtosis=3.0,
        ),
    ],
    ids=["expected_max", "margin", "probability"],
)
def accounting_entry(request):
    return request.param


@pytest.mark.parametrize("count", [0, -1, True, np.bool_(True), 1.5, np.nan, np.inf, "1"])
def test_dsr_accounting_rejects_nonpositive_or_nonintegral_count(accounting_entry, count) -> None:
    with pytest.raises(ValueError, match="n_trials must be"):
        accounting_entry(n_trials=count, sr_std=0.2)


@pytest.mark.parametrize("count", [1, 10])
@pytest.mark.parametrize("dispersion", [0.0, -0.2, np.nan, np.inf, -np.inf, True, "0.2", 0.2 + 1j])
def test_dsr_accounting_rejects_invalid_dispersion_before_shortcut(
    accounting_entry, count, dispersion
) -> None:
    with pytest.raises(ValueError, match="sr_std must be"):
        accounting_entry(n_trials=count, sr_std=dispersion)


def test_dsr_accounting_preserves_numpy_and_fraction_inputs(accounting_entry) -> None:
    from fractions import Fraction

    expected = accounting_entry(n_trials=5, sr_std=0.2)
    assert accounting_entry(n_trials=np.int64(5), sr_std=np.float64(0.2)) == expected
    assert accounting_entry(n_trials=5, sr_std=Fraction(1, 5)) == expected


def test_valid_one_trial_probability_matches_unpenalized_psr() -> None:
    expected = probabilistic_sharpe_ratio(
        0.2, benchmark_sr=0.0, n_returns=100, skew=0.0, kurtosis=3.0
    )
    assert expected_max_sharpe(1, 0.2) == 0.0
    assert deflated_sharpe(0.2, 1, 0.2) == 0.2
    assert (
        deflated_sharpe_probability(
            0.2, n_trials=1, sr_std=0.2, n_returns=100, skew=0.0, kurtosis=3.0
        )
        == expected
    )


@pytest.mark.parametrize(
    "count", [10**17, 10**300, 10**309], ids=["large", "extreme", "beyond_float_max"]
)
def test_expected_max_large_count_matches_forward_gaussian_tail_oracle(count) -> None:
    from scipy.optimize import brentq

    # Independently invert the forward Gaussian survival function, without ppf/isf.
    def quantile(tail):
        return brentq(
            lambda z: math.erfc(z / math.sqrt(2.0)) / 2.0 - tail,
            0.0,
            40.0,
            xtol=1e-13,
        )

    tail = 1 / count
    a, b = quantile(tail), quantile(tail / math.e)
    gamma = 0.5772156649015329
    expected = 0.2 * ((1.0 - gamma) * a + gamma * b)
    actual = expected_max_sharpe(count, 0.2)
    assert math.isfinite(actual)
    assert actual == pytest.approx(expected, rel=1e-13)


def test_expected_max_declines_unrepresentable_trial_tail() -> None:
    with pytest.raises(ValueError, match="trial tails must be positive and finite"):
        expected_max_sharpe(10**400, 0.2)


def test_expected_max_declines_nonfinite_scaled_haircut(accounting_entry) -> None:
    with pytest.raises(ValueError, match="expected maximum Sharpe must be finite"):
        accounting_entry(n_trials=100, sr_std=1e308)


@pytest.mark.parametrize("count", [2.5, True, np.bool_(True), np.nan, np.inf, "100"])
def test_psr_rejects_nonintegral_observed_history(count) -> None:
    with pytest.raises(ValueError, match="n_returns must be"):
        probabilistic_sharpe_ratio(0.2, benchmark_sr=0.0, n_returns=count, skew=0.0, kurtosis=3.0)


@pytest.mark.parametrize("field", ["observed_sr", "benchmark_sr", "skew", "kurtosis"])
@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, True, "0.2", 0.2 + 1j])
def test_psr_rejects_invalid_original_scalar_evidence(field, invalid) -> None:
    inputs = {
        "observed_sr": 0.2,
        "benchmark_sr": 0.0,
        "n_returns": 100,
        "skew": 0.0,
        "kurtosis": 3.0,
    }
    inputs[field] = invalid
    with pytest.raises(ValueError, match=field + " must be"):
        probabilistic_sharpe_ratio(**inputs)


def test_psr_count_precedes_invalid_moment_evidence() -> None:
    with pytest.raises(ValueError, match="n_returns must be"):
        probabilistic_sharpe_ratio(
            0.2, benchmark_sr=0.0, n_returns=2.5, skew=np.nan, kurtosis=np.inf
        )


@pytest.mark.parametrize("field", ["observed_sr", "skew", "kurtosis"])
def test_probability_dsr_inherits_psr_source_validation(field) -> None:
    inputs = {
        "observed_sr": 0.2,
        "n_trials": 10,
        "sr_std": 0.2,
        "n_returns": 100,
        "skew": 0.0,
        "kurtosis": 3.0,
    }
    inputs[field] = np.inf
    with pytest.raises(ValueError, match=field + " must be"):
        deflated_sharpe_probability(**inputs)


def test_psr_preserves_numpy_fraction_and_signed_source_oracle() -> None:
    from fractions import Fraction

    observed, benchmark, n, skew, kurtosis = -0.1, -0.2, 401, -0.4, 6.0
    standard_error = math.sqrt(
        (1 - skew * observed + 0.25 * (kurtosis - 1) * observed**2) / (n - 1)
    )
    expected = float(norm.cdf((observed - benchmark) / standard_error))
    assert probabilistic_sharpe_ratio(
        np.float64(observed),
        benchmark_sr=Fraction(-1, 5),
        n_returns=np.int64(n),
        skew=np.float64(skew),
        kurtosis=Fraction(6),
    ) == pytest.approx(expected)


@pytest.mark.parametrize("count", [1, 10])
@pytest.mark.parametrize(
    "observed", [True, np.bool_(True), np.nan, np.inf, -np.inf, "0.2", 0.2 + 1j]
)
def test_margin_dsr_rejects_malformed_observed_score(count, observed) -> None:
    with pytest.raises(ValueError, match="observed_sr must be"):
        deflated_sharpe(observed, n_trials=count, sr_std=0.2)


def test_margin_dsr_declines_nonfinite_native_difference() -> None:
    with (
        np.errstate(all="raise"),
        pytest.raises(ValueError, match="deflated Sharpe margin must be finite"),
    ):
        deflated_sharpe(-1.5e308, n_trials=2, sr_std=1e308)


def test_margin_dsr_accounting_errors_precede_invalid_score() -> None:
    with pytest.raises(ValueError, match="n_trials must be"):
        deflated_sharpe(np.nan, n_trials=0, sr_std=0.2)
    with pytest.raises(ValueError, match="sr_std must be"):
        deflated_sharpe(np.nan, n_trials=1, sr_std=np.nan)


@pytest.mark.parametrize("observed", [-0.2, 0.0, 0.2])
def test_margin_dsr_preserves_signed_fraction_and_numpy_source_oracle(observed) -> None:
    from fractions import Fraction

    haircut = expected_max_sharpe(5, 0.2)
    expected = observed - max(haircut, 0.0)
    assert deflated_sharpe(np.float64(observed), n_trials=5, sr_std=0.2) == expected
    assert deflated_sharpe(Fraction(str(observed)), n_trials=5, sr_std=0.2) == expected
    assert deflated_sharpe(observed, n_trials=1, sr_std=0.2) == observed


def test_margin_dsr_refuses_unrepresentable_real_observed_score() -> None:
    with pytest.raises(ValueError, match="observed_sr must be"):
        deflated_sharpe(10**400, n_trials=1, sr_std=0.2)


@pytest.mark.parametrize(
    ("observed", "skew", "kurtosis", "count"),
    [
        (1e153, 0.0, 1e10, 100),
        (1e308, 0.0, 3.0, 100),
        (0.2, 1e308, 1e308, 100),
        (0.2, 0.0, 3.0, 10**400),
        (1.0, 2.0, math.nextafter(5.0, math.inf), int(1.79e308)),
    ],
)
def test_psr_declines_unmeasurable_native_arithmetic(observed, skew, kurtosis, count) -> None:
    with pytest.raises(ValueError, match="PSR arithmetic must be finite and measurable"):
        probabilistic_sharpe_ratio(
            observed, benchmark_sr=0.0, n_returns=count, skew=skew, kurtosis=kurtosis
        )


def test_probability_dsr_propagates_unmeasurable_standard_error() -> None:
    with pytest.raises(ValueError, match="PSR arithmetic must be finite and measurable"):
        deflated_sharpe_probability(
            1e153, n_trials=1, sr_std=0.2, n_returns=100, skew=0.0, kurtosis=1e10
        )


@pytest.mark.parametrize(("benchmark", "probability"), [(-1e308, 1.0), (1e308, 0.0)])
def test_psr_preserves_gaussian_tail_saturation(benchmark, probability) -> None:
    assert (
        probabilistic_sharpe_ratio(
            0.2, benchmark_sr=benchmark, n_returns=100, skew=0.0, kurtosis=3.0
        )
        == probability
    )


@given(observed=st.floats(min_value=-5, max_value=5, allow_nan=False, allow_infinity=False))
def test_psr_finite_arithmetic_matches_independent_erfc_oracle(observed: float) -> None:
    # Normal moments: independently standardize using hypot, then evaluate Gaussian erfc.
    se = math.hypot(1.0, observed / math.sqrt(2.0)) / math.sqrt(99.0)
    expected = 0.5 * math.erfc(-(observed - 0.03) / se / math.sqrt(2.0))
    assert probabilistic_sharpe_ratio(
        observed, benchmark_sr=0.03, n_returns=100, skew=0.0, kurtosis=3.0
    ) == pytest.approx(expected, abs=1e-15)
