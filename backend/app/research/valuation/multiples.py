"""Valuation multiples ranked against a company's OWN history (ADR-022).

The *current* P/E and P/S (from the live price and the latest filing) are percentile-ranked
within the company's historical distribution of that multiple — each past year's price joined
with that year's figure. A low percentile flags "cheap versus its own past". Peer-relative
multiples and EV/EBITDA are deferred (ADR-022). Honest per rule 6 — it flags a potential signal.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory


class MultiplesResult(BaseModel):
    """Current multiples and where each sits within the company's own history."""

    model_config = ConfigDict(frozen=True)

    pe_ratio: float | None
    pe_percentile: float | None
    pe_history_n: int
    ps_ratio: float | None
    ps_percentile: float | None
    ps_history_n: int
    flags: list[str]


def percentile_rank(value: float, series: Sequence[float]) -> float:
    """Fraction of ``series`` strictly below ``value``, in [0, 1]. 0 means ``value`` is the
    cheapest observation, so for a valuation multiple a low rank flags relative cheapness."""
    return sum(1 for x in series if x < value) / len(series)


def _ranked(
    current: float | None, series: Sequence[float], label: str, flags: list[str]
) -> float | None:
    """Percentile of ``current`` within ``series``; None (with a flag) when history is too thin."""
    if current is None:
        return None
    if len(series) < 2:
        flags.append(f"insufficient {label} history for a percentile")
        return None
    return percentile_rank(current, series)


def compute_multiples(history: FundamentalsHistory, price: float) -> MultiplesResult:
    """Current P/E and P/S for ``price`` vs the latest filing, each ranked against own history."""
    latest = history.years[-1]
    flags: list[str] = []

    # --- P/E ---
    pe_ratio: float | None = None
    if latest.eps is None:
        flags.append("EPS unavailable — P/E not computed")
    elif latest.eps <= 0:
        flags.append("non-positive EPS — P/E not meaningful")
    else:
        pe_ratio = price / latest.eps
    pe_hist = [
        y.price / y.eps
        for y in history.years
        if y.price is not None and y.price > 0 and y.eps is not None and y.eps > 0
    ]
    pe_percentile = _ranked(pe_ratio, pe_hist, "P/E", flags)

    # --- P/S (market cap / revenue) ---
    ps_ratio: float | None = None
    if latest.shares_diluted is None:
        flags.append("shares outstanding unavailable — P/S not computed")
    elif latest.revenue <= 0:
        flags.append("non-positive revenue — P/S not meaningful")
    else:
        ps_ratio = price * latest.shares_diluted / latest.revenue
    ps_hist = [
        y.price * y.shares_diluted / y.revenue
        for y in history.years
        if y.price is not None
        and y.price > 0
        and y.shares_diluted is not None
        and y.shares_diluted > 0
        and y.revenue > 0
    ]
    ps_percentile = _ranked(ps_ratio, ps_hist, "P/S", flags)

    return MultiplesResult(
        pe_ratio=pe_ratio,
        pe_percentile=pe_percentile,
        pe_history_n=len(pe_hist),
        ps_ratio=ps_ratio,
        ps_percentile=ps_percentile,
        ps_history_n=len(ps_hist),
        flags=flags,
    )
