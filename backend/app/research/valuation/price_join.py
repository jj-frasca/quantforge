"""Join market prices onto a FundamentalsHistory at each fiscal-year end (ADR-022).

EDGAR carries no prices, but the multiples-vs-own-history percentiles need the close near each
fiscal period end. The caller supplies an ascending ``(date, close)`` series (built from whatever
price adapter it uses); this stays decoupled from the price layer and fully unit-testable.
"""

import bisect
from collections.abc import Sequence
from datetime import date

from app.data.fundamentals import FundamentalsHistory


def asof_close(closes: Sequence[tuple[date, float]], target: date) -> float | None:
    """Close of the last bar on or before ``target``. None when no bar precedes it.

    ``closes`` must be in ascending date order (raises ValueError otherwise).
    """
    dates = [d for d, _ in closes]
    if any(dates[i] > dates[i + 1] for i in range(len(dates) - 1)):
        raise ValueError("closes must be in ascending date order")
    index = bisect.bisect_right(dates, target)
    if index == 0:
        return None
    return closes[index - 1][1]


def attach_fiscal_year_prices(
    history: FundamentalsHistory, closes: Sequence[tuple[date, float]]
) -> FundamentalsHistory:
    """Return a copy of ``history`` with each year's ``price`` set to the close at its
    ``period_end``. Years without a period end, or with no bar on/before it, keep ``price`` None."""
    years = tuple(
        year.model_copy(update={"price": asof_close(closes, year.period_end)})
        if year.period_end is not None
        else year
        for year in history.years
    )
    return history.model_copy(update={"years": years})
