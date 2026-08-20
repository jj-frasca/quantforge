"""ADR-046 whole-search DSR pricing: one common haircut, cumulative effort, invalid inputs."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.trial_accounting import whole_search_deflated_sharpes


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
