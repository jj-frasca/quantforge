"""Whole-search multiple-testing accounting (ADR-046/050)."""

from app.validation.deflated_sharpe import deflated_sharpe, robust_sharpe_dispersion


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
