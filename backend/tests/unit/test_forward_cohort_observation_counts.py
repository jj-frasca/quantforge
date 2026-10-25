"""Cohort performance needs observed forward bars, not merely a score (ADR-366)."""

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.lab.paper import ForwardScore, PaperPosition
from app.research.lab.portfolio_manager import deflation_cohorts


def _position(
    symbol: str,
    verdict: bool | None,
    *,
    bars: int | None,
    sharpe: float = 0.0,
    trades: int = 0,
) -> PaperPosition:
    score = None
    if bars is not None:
        score = ForwardScore(
            forward_bars=bars,
            forward_return=0.0,
            forward_sharpe=sharpe,
            buy_and_hold_return=0.0,
            buy_and_hold_sharpe=0.0,
            beats_buy_and_hold=False,
            forward_trades=trades,
            as_of=datetime(2026, 1, 5, tzinfo=UTC),
        )
    return PaperPosition(
        symbol=symbol,
        strategy_name="momentum",
        parameters={"lookback": 3, "skip": 0},
        frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
        survives_universe_deflation=verdict,
        score=score,
    )


def _mean(book: list[PaperPosition], verdict: bool) -> float | None:
    result = deflation_cohorts(book)
    return (
        result.survivor_mean_forward_sharpe if verdict else result.non_survivor_mean_forward_sharpe
    )


@pytest.mark.parametrize("verdict", [True, False])
def test_cohort_given_zero_bar_only_score_reports_unmeasured_mean(verdict: bool) -> None:
    position = _position("A", verdict, bars=0)
    assert _mean([position], verdict) is None
    cohorts = deflation_cohorts([position])
    assert (cohorts.n_survivors, cohorts.n_non_survivors) == ((1, 0) if verdict else (0, 1))


@pytest.mark.parametrize("verdict", [True, False])
def test_cohort_given_unobserved_placeholder_does_not_dilute_measured_mean(verdict: bool) -> None:
    measured = _position("A", verdict, bars=4, sharpe=4.0)
    absent = _position("B", verdict, bars=None)
    zero_bar = _position("B", verdict, bars=0)
    assert _mean([measured, absent], verdict) == 4.0
    assert _mean([measured, zero_bar], verdict) == 4.0


@pytest.mark.parametrize("verdict", [True, False])
def test_cohort_given_zero_bar_legacy_nonzero_scalar_still_has_no_observations(
    verdict: bool,
) -> None:
    assert _mean([_position("A", verdict, bars=0, sharpe=3.0)], verdict) is None


@pytest.mark.parametrize("verdict", [True, False])
@pytest.mark.parametrize("bars", [1, 4, 126])
@pytest.mark.parametrize("trades", [0, 1])
def test_cohort_given_positive_bars_preserves_measured_zero_and_zero_trade_scores(
    verdict: bool, bars: int, trades: int
) -> None:
    book = [
        _position("A", verdict, bars=bars, sharpe=4.0, trades=trades),
        _position("B", verdict, bars=bars, sharpe=0.0, trades=trades),
    ]
    before = [position.model_dump_json() for position in book]
    assert _mean(book, verdict) == 2.0
    assert [position.model_dump_json() for position in book] == before


def test_cohort_given_unknown_verdict_preserves_membership_without_assigning_mean() -> None:
    book = [_position("A", None, bars=4, sharpe=4.0), _position("B", None, bars=0)]
    result = deflation_cohorts(book)
    assert result.n_unknown == 2
    assert result.n_survivors == result.n_non_survivors == 0
    assert result.survivor_mean_forward_sharpe is None
    assert result.non_survivor_mean_forward_sharpe is None


@given(
    values=st.lists(
        st.floats(min_value=-20.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=8,
    ),
    placeholders=st.integers(min_value=1, max_value=5),
    verdict=st.booleans(),
)
@settings(max_examples=35, deadline=None)
def test_cohort_mean_is_unchanged_by_adding_unobserved_placeholders(
    values: list[float], placeholders: int, verdict: bool
) -> None:
    measured = [_position(f"M{i}", verdict, bars=4, sharpe=value) for i, value in enumerate(values)]
    unobserved = [_position(f"U{i}", verdict, bars=0) for i in range(placeholders)]
    assert _mean(measured + unobserved, verdict) == _mean(measured, verdict)
    result = deflation_cohorts(measured + unobserved)
    assert (result.n_survivors if verdict else result.n_non_survivors) == len(values) + placeholders
