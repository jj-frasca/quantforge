"""The detectable-edge frontier (ADR-043): what must be TRUE for the gate to fire, as opposed to
what must be OBSERVED (the ADR-018 bar). The difference between the two is the estimation noise
that makes a Sharpe-1.7 edge fail a 1.7 bar half the time."""

import math

import pytest

from app.research.lab.frontier import (
    DetectionFrontier,
    describe_frontier,
    detectable_sharpe,
    sharpe_standard_error,
)
from app.research.lab.universe import expected_max_sharpe_under_null


def test_standard_error_at_the_null_is_the_bar_formula() -> None:
    """ADR-043's central claim of consistency: Lo's SE evaluated at SR = 0 is exactly the sqrt(1/T)
    that expected_max_sharpe_under_null already uses. If these ever diverge, one of them is wrong."""
    assert sharpe_standard_error(0.0, 4.3) == pytest.approx(math.sqrt(1.0 / 4.3))


def test_standard_error_grows_with_the_true_sharpe() -> None:
    """Lo's SR^2/2 term: a large true Sharpe is estimated less precisely, which matters precisely
    at the large effect sizes this pipeline can see at all."""
    assert sharpe_standard_error(3.0, 4.3) > sharpe_standard_error(0.5, 4.3)


def test_standard_error_shrinks_with_more_history() -> None:
    assert sharpe_standard_error(1.0, 10.0) < sharpe_standard_error(1.0, 2.5)


def test_detectable_sharpe_sits_above_the_bar_it_must_clear() -> None:
    """The whole point: clearing a bar in expectation is a 50% proposition, so 80% power costs
    roughly z_0.8 standard errors on top of the bar."""
    bar = expected_max_sharpe_under_null(607, 4.3)
    detectable = detectable_sharpe(607, 4.3)
    assert detectable > bar
    assert detectable == pytest.approx(
        bar + 0.8416 * sharpe_standard_error(detectable, 4.3), abs=1e-3
    )


def test_detectable_sharpe_at_fifty_percent_power_is_the_bar() -> None:
    """z = 0 at p = 0.5: half the time a true edge exactly at the bar is estimated above it."""
    bar = expected_max_sharpe_under_null(607, 4.3)
    assert detectable_sharpe(607, 4.3, power=0.5) == pytest.approx(bar, abs=1e-6)


def test_history_is_a_stronger_lever_than_universe_size() -> None:
    """ADR-043's design finding, asserted so a future session cannot quietly assume otherwise:
    halving the universe buys a few percent, doubling the holdout buys ~29%."""
    base = detectable_sharpe(607, 4.3)
    halved_universe = detectable_sharpe(304, 4.3)
    doubled_history = detectable_sharpe(607, 8.6)
    assert 0.90 < halved_universe / base < 1.0
    assert doubled_history / base < 0.75


def test_more_hypotheses_raise_the_detectable_edge() -> None:
    assert detectable_sharpe(2000, 4.3) > detectable_sharpe(200, 4.3)


def test_describe_frontier_reports_the_bar_beside_what_must_be_true() -> None:
    frontier = describe_frontier(607, 4.3)
    assert isinstance(frontier, DetectionFrontier)
    assert frontier.n_symbols == 607
    assert frontier.holdout_years == 4.3
    assert frontier.power == 0.8
    assert frontier.bar == pytest.approx(expected_max_sharpe_under_null(607, 4.3))
    assert frontier.detectable_sharpe == pytest.approx(detectable_sharpe(607, 4.3))
    assert frontier.standard_error == pytest.approx(
        sharpe_standard_error(frontier.detectable_sharpe, 4.3)
    )


def test_a_universe_too_small_to_deflate_still_needs_an_edge_above_zero() -> None:
    """The bar is 0.0 below two symbols (nothing was selected across), but estimation noise does not
    vanish — reporting 0.0 as the detectable edge would claim a coin flip is detectable."""
    assert detectable_sharpe(1, 4.3) > 0.0


def test_frontier_refuses_impossible_inputs() -> None:
    with pytest.raises(ValueError, match="holdout_years"):
        detectable_sharpe(607, 0.0)
    with pytest.raises(ValueError, match="power"):
        detectable_sharpe(607, 4.3, power=0.0)
    with pytest.raises(ValueError, match="power"):
        detectable_sharpe(607, 4.3, power=1.0)
    with pytest.raises(ValueError, match="holdout_years"):
        sharpe_standard_error(1.0, -1.0)
