"""ADR-046 whole-search DSR pricing: one common haircut, cumulative effort, invalid inputs —
and ADR-054's probability form priced off the same search at the same haircut."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.backtesting.metrics import TRADING_DAYS, ReturnMoments
from app.research.lab.trial_accounting import (
    whole_search_deflated_sharpe_probabilities,
    whole_search_deflated_sharpes,
)
from app.validation.deflated_sharpe import deflated_sharpe_probability, robust_sharpe_dispersion


@given(
    first=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    second=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    lifetime=st.integers(min_value=2, max_value=100_000),
)
def test_whole_search_finalists_receive_one_common_haircut(
    first: float, second: float, lifetime: int
) -> None:
    candidate_sharpes = [first, second, -0.75, 0.25]
    priced = whole_search_deflated_sharpes([first, second], candidate_sharpes, lifetime)
    assert math.isfinite(priced[0]) and math.isfinite(priced[1])
    assert first - priced[0] == pytest.approx(second - priced[1])


def test_more_lifetime_trials_increase_the_whole_search_haircut() -> None:
    candidates = [-0.5, 0.0, 0.5, 1.0]
    first = whole_search_deflated_sharpes([1.0], candidates, 4)[0]
    repeated = whole_search_deflated_sharpes([1.0], candidates, 4_000)[0]
    assert repeated < first


def test_whole_search_haircut_resists_one_signal_contaminated_tail() -> None:
    baseline = [-1.0, -0.5, 0.0, 0.5, 1.0]
    contaminated = [-1.0, -0.5, 0.0, 0.5, 100.0]
    baseline_price = whole_search_deflated_sharpes([1.0], baseline, 200)[0]
    contaminated_price = whole_search_deflated_sharpes([1.0], contaminated, 200)[0]
    assert contaminated_price == pytest.approx(baseline_price)


@pytest.mark.parametrize(
    ("finalists", "candidates", "message"),
    [([], [0.0, 1.0], "finalist"), ([1.0], [1.0], "candidate")],
)
def test_whole_search_pricing_rejects_an_unmeasurable_family(
    finalists: list[float], candidates: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        whole_search_deflated_sharpes(finalists, candidates, 2)


# --- ADR-054 decision 3: the probability form, priced on the same search ---


def _normal_moments(n: int = 2000) -> ReturnMoments:
    return ReturnMoments(n_returns=n, skew=0.0, kurtosis=3.0)


def test_probabilities_are_probabilities() -> None:
    candidates = [-0.5, 0.0, 0.5, 1.0]
    priced = whole_search_deflated_sharpe_probabilities(
        [1.0, 0.5], [_normal_moments(), _normal_moments()], candidates, 200
    )
    assert all(p is not None and 0.0 <= p <= 1.0 for p in priced)


def test_the_probability_de_annualizes_the_sharpe_and_the_dispersion_together() -> None:
    """The trap ADR-054 names: `Trial` fields are annualized, PSR is per-period. Passing the
    annualized Sharpe with per-period moments must NOT be what this function computes."""
    candidates = [-0.5, 0.0, 0.5, 1.0]
    moments = _normal_moments()
    priced = whole_search_deflated_sharpe_probabilities([1.0], [moments], candidates, 200)[0]
    sr_std = robust_sharpe_dispersion(candidates)
    expected = deflated_sharpe_probability(
        1.0 / math.sqrt(TRADING_DAYS),
        n_trials=200,
        sr_std=sr_std / math.sqrt(TRADING_DAYS),
        n_returns=moments.n_returns,
        skew=moments.skew,
        kurtosis=moments.kurtosis,
    )
    assert priced == pytest.approx(expected)


def test_more_lifetime_trials_lower_the_probability() -> None:
    candidates = [-0.5, 0.0, 0.5, 1.0]
    few = whole_search_deflated_sharpe_probabilities([1.0], [_normal_moments()], candidates, 4)[0]
    many = whole_search_deflated_sharpe_probabilities(
        [1.0], [_normal_moments()], candidates, 4_000
    )[0]
    assert few is not None and many is not None
    assert many < few


def test_the_probability_and_the_margin_agree_on_which_finalist_is_better() -> None:
    """Both price the same search with the same haircut, so at equal track records the ordering
    must be the observed-Sharpe ordering. Their DISAGREEMENT is about the bar, not the ranking."""
    candidates = [-0.5, 0.0, 0.5, 1.0]
    moments = [_normal_moments(), _normal_moments()]
    margins = whole_search_deflated_sharpes([1.2, 0.4], candidates, 200)
    probabilities = whole_search_deflated_sharpe_probabilities([1.2, 0.4], moments, candidates, 200)
    assert margins[0] > margins[1]
    assert probabilities[0] is not None and probabilities[1] is not None
    assert probabilities[0] > probabilities[1]


def test_an_unmeasured_finalist_stays_unmeasured() -> None:
    """A family whose finalist has no estimable moments records None, not a fabricated number."""
    priced = whole_search_deflated_sharpe_probabilities(
        [1.0, 0.5], [None, _normal_moments()], [-0.5, 0.0, 0.5, 1.0], 200
    )
    assert priced[0] is None
    assert priced[1] is not None


def test_a_degenerate_moment_combination_is_unmeasured_rather_than_certain() -> None:
    """kurtosis - skew^2 - 1 <= 0 is not a distribution; the paper's formula refuses it and this
    must surface as 'not measured' rather than crashing a whole hunt."""
    priced = whole_search_deflated_sharpe_probabilities(
        [1.0], [ReturnMoments(n_returns=500, skew=0.0, kurtosis=0.5)], [-0.5, 0.0, 0.5, 1.0], 200
    )
    assert priced == [None]


def test_probability_pricing_rejects_a_mismatched_moment_list() -> None:
    with pytest.raises(ValueError, match="finalist"):
        whole_search_deflated_sharpe_probabilities(
            [1.0, 0.5], [_normal_moments()], [-0.5, 0.0, 0.5, 1.0], 200
        )
