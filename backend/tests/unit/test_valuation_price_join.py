"""Join market prices onto a FundamentalsHistory at each fiscal-year end (ADR-022).

EDGAR carries no prices; the multiples-vs-own-history percentiles need the close near each
fiscal period end. Pure + deterministic — the caller supplies an ascending (date, close) series.
"""

from datetime import date

import pytest

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.valuation.price_join import asof_close, attach_fiscal_year_prices

_CLOSES = [
    (date(2022, 9, 29), 40.0),
    (date(2022, 9, 30), 41.0),
    (date(2023, 9, 29), 50.0),
    (date(2024, 9, 30), 60.0),
]


def test_asof_close_exact_match() -> None:
    assert asof_close(_CLOSES, date(2024, 9, 30)) == 60.0


def test_asof_close_between_dates_picks_the_last_on_or_before() -> None:
    # target between 2023-09-29 and 2024-09-30 -> the 2023 close (last on/before)
    assert asof_close(_CLOSES, date(2024, 1, 15)) == 50.0


def test_asof_close_before_all_bars_is_none() -> None:
    assert asof_close(_CLOSES, date(2000, 1, 1)) is None


def test_asof_close_after_all_bars_picks_the_last() -> None:
    assert asof_close(_CLOSES, date(2030, 1, 1)) == 60.0


def _history(years: list[AnnualFundamentals]) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="AAPL",
        cik=320193,
        entity_name="Apple Inc.",
        form="10-K",
        accession_number="a-2024",
        source_url="https://sec.gov/x",
        years=tuple(years),
    )


def test_attach_populates_price_at_each_fiscal_year_end() -> None:
    hist = _history(
        [
            AnnualFundamentals(fiscal_year=2023, period_end=date(2023, 9, 29), revenue=1100.0),
            AnnualFundamentals(fiscal_year=2024, period_end=date(2024, 9, 30), revenue=1200.0),
        ]
    )
    joined = attach_fiscal_year_prices(hist, _CLOSES)
    assert [y.price for y in joined.years] == [50.0, 60.0]
    # other fields and citation preserved
    assert joined.years[0].revenue == 1100.0
    assert joined.accession_number == "a-2024"
    # input history is not mutated
    assert hist.years[0].price is None


def test_attach_leaves_price_none_when_no_bar_on_or_before_period_end() -> None:
    hist = _history(
        [AnnualFundamentals(fiscal_year=1999, period_end=date(1999, 12, 31), revenue=10.0)]
    )
    joined = attach_fiscal_year_prices(hist, _CLOSES)
    assert joined.years[0].price is None


def test_attach_leaves_price_none_when_period_end_missing() -> None:
    hist = _history([AnnualFundamentals(fiscal_year=2024, period_end=None, revenue=1200.0)])
    joined = attach_fiscal_year_prices(hist, _CLOSES)
    assert joined.years[0].price is None


def test_attach_with_empty_closes_leaves_all_prices_none() -> None:
    hist = _history(
        [AnnualFundamentals(fiscal_year=2024, period_end=date(2024, 9, 30), revenue=1200.0)]
    )
    joined = attach_fiscal_year_prices(hist, [])
    assert joined.years[0].price is None


def test_asof_close_requires_ascending_dates() -> None:
    with pytest.raises(ValueError, match="ascending"):
        asof_close([(date(2024, 1, 1), 1.0), (date(2023, 1, 1), 2.0)], date(2024, 6, 1))
