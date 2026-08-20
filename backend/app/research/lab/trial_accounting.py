"""Whole-search multiple-testing accounting (ADR-046/050/054)."""

import math

from app.research.backtesting.metrics import TRADING_DAYS, ReturnMoments
from app.validation.deflated_sharpe import (
    deflated_sharpe,
    deflated_sharpe_probability,
    robust_sharpe_dispersion,
)


def whole_search_deflated_sharpes(
    finalist_sharpes: list[float], candidate_sharpes: list[float], lifetime_trials: int
) -> list[float]:
    """Apply one common lifetime DSR haircut to a search's family finalists.

    Notes:
        ``candidate_sharpes`` contains every concrete configuration evaluated in the current run;
        it estimates the null trial dispersion with ADR-050's Normal-consistent robust scale.
        ``lifetime_trials`` supplies the cumulative selection breadth. Historical candidate
        distributions were not persisted, so combining them here would require invented data;
        ADR-046 records the current-run dispersion approximation.
    """
    if not finalist_sharpes:
        raise ValueError("need at least one family finalist")
    if len(candidate_sharpes) < 2:
        raise ValueError("need at least two candidate Sharpes")
    sr_std = robust_sharpe_dispersion(candidate_sharpes)
    return [deflated_sharpe(sharpe, lifetime_trials, sr_std) for sharpe in finalist_sharpes]


def whole_search_deflated_sharpe_probabilities(
    finalist_sharpes: list[float],
    finalist_moments: list[ReturnMoments | None],
    candidate_sharpes: list[float],
    lifetime_trials: int,
) -> list[float | None]:
    """The paper's probability-form DSR for each family finalist (ADR-054 decision 3).

    Notes:
        SCALE: ``finalist_sharpes`` and the dispersion estimated from ``candidate_sharpes`` are
        ANNUALIZED, while the PSR is a function of the per-period Sharpe and the per-period
        moments TOGETHER. Both are divided by the same ``sqrt(TRADING_DAYS)`` here — annualizing
        one input and not the others silently rescales the probability rather than failing, which
        is the class of error ADR-054 exists to remove.
        The dispersion is recomputed from the same candidates the margin form uses; it is a pure
        function of that list, so the two haircuts cannot disagree.
        A finalist whose moments are absent, or whose moment combination the paper's formula
        refuses, records None. One unmeasurable family must not fabricate a probability, and must
        not abort a hunt over the other families that are measurable.
    """
    if len(finalist_moments) != len(finalist_sharpes):
        raise ValueError("need one moment summary per finalist")
    sr_std = robust_sharpe_dispersion(candidate_sharpes)
    scale = math.sqrt(TRADING_DAYS)
    probabilities: list[float | None] = []
    for sharpe, moments in zip(finalist_sharpes, finalist_moments, strict=True):
        if moments is None:
            probabilities.append(None)
            continue
        try:
            probabilities.append(
                deflated_sharpe_probability(
                    sharpe / scale,
                    n_trials=lifetime_trials,
                    sr_std=sr_std / scale,
                    n_returns=moments.n_returns,
                    skew=moments.skew,
                    kurtosis=moments.kurtosis,
                )
            )
        except ValueError:
            probabilities.append(None)
    return probabilities
