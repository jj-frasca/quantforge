"""Current P/E and P/S percentile-ranked against the company's OWN history (ADR-022).
Peer-relative multiples are deferred; this is self-history only. Pure + deterministic."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.valuation.multiples import (
    MultiplesResult,
    compute_multiples,
    percentile_rank,
)


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


def _y(
    fy: int, *, eps: float, price: float, shares: float = 100.0, revenue: float
) -> AnnualFundamentals:
    return AnnualFundamentals(
        fiscal_year=fy, revenue=revenue, eps=eps, price=price, shares_diluted=shares
    )


def test_percentile_rank_is_fraction_strictly_below() -> None:
    assert percentile_rank(11.0, [10.0, 10.0, 12.0]) == pytest.approx(2 / 3)
    assert percentile_rank(5.0, [10.0, 20.0]) == 0.0
    assert percentile_rank(100.0, [10.0, 20.0]) == 1.0


@given(
    value=st.floats(min_value=-1e6, max_value=1e6),
    series=st.lists(st.floats(min_value=-1e6, max_value=1e6), min_size=1, max_size=20),
)
def test_percentile_rank_in_unit_interval(value: float, series: list[float]) -> None:
    assert 0.0 <= percentile_rank(value, series) <= 1.0


def _three_year() -> FundamentalsHistory:
    return _history(
        [
            _y(2022, eps=4.0, price=40.0, revenue=1000.0),
            _y(2023, eps=5.0, price=50.0, revenue=1100.0),
            _y(2024, eps=5.0, price=60.0, revenue=1200.0),
        ]
    )


def test_current_multiples_ranked_against_own_history() -> None:
    result = compute_multiples(_three_year(), price=55.0)
    assert isinstance(result, MultiplesResult)
    # current P/E = 55 / 5 = 11 vs history [10, 10, 12]
    assert result.pe_ratio == pytest.approx(11.0)
    assert result.pe_history_n == 3
    assert result.pe_percentile == pytest.approx(2 / 3)
    # current P/S = 55 * 100 / 1200 vs history [4.0, 4.5454.., 5.0]
    assert result.ps_ratio == pytest.approx(5500 / 1200)
    assert result.ps_history_n == 3
    assert result.ps_percentile == pytest.approx(2 / 3)
    assert result.flags == []


def test_non_positive_eps_leaves_pe_none_and_flags() -> None:
    hist = _history(
        [
            _y(2023, eps=5.0, price=50.0, revenue=1100.0),
            _y(2024, eps=-1.0, price=60.0, revenue=1200.0),
        ]
    )
    result = compute_multiples(hist, price=55.0)
    assert result.pe_ratio is None
    assert result.pe_percentile is None
    assert any("earnings" in f.lower() or "eps" in f.lower() for f in result.flags)
    # the negative-EPS year is excluded from the P/E history distribution
    assert result.pe_history_n == 1


def test_missing_eps_leaves_pe_none_and_flags() -> None:
    hist = _history(
        [AnnualFundamentals(fiscal_year=2024, revenue=1200.0, price=60.0, shares_diluted=100.0)]
    )
    result = compute_multiples(hist, price=55.0)
    assert result.pe_ratio is None
    assert any("eps" in f.lower() for f in result.flags)


def test_years_without_price_are_excluded_from_history() -> None:
    hist = _history(
        [
            AnnualFundamentals(fiscal_year=2022, revenue=1000.0, eps=4.0, shares_diluted=100.0),
            _y(2023, eps=5.0, price=50.0, revenue=1100.0),
            _y(2024, eps=5.0, price=60.0, revenue=1200.0),
        ]
    )
    result = compute_multiples(hist, price=55.0)
    assert result.pe_history_n == 2  # 2022 has no price


def test_single_history_point_gives_no_percentile_but_flags() -> None:
    result = compute_multiples(
        _history([_y(2024, eps=5.0, price=60.0, revenue=1200.0)]), price=55.0
    )
    assert result.pe_ratio == pytest.approx(11.0)
    assert result.pe_percentile is None
    assert result.ps_percentile is None
    assert any("history" in f.lower() for f in result.flags)


def test_non_positive_revenue_leaves_ps_none_and_flags() -> None:
    hist = _history([_y(2024, eps=5.0, price=60.0, shares=100.0, revenue=0.0)])
    result = compute_multiples(hist, price=55.0)
    assert result.ps_ratio is None
    assert any("revenue" in f.lower() for f in result.flags)


def test_missing_shares_leaves_ps_none_and_flags() -> None:
    hist = _history(
        [
            AnnualFundamentals(fiscal_year=2023, revenue=1100.0, eps=5.0, price=50.0),
            AnnualFundamentals(fiscal_year=2024, revenue=1200.0, eps=5.0, price=60.0),
        ]
    )
    result = compute_multiples(hist, price=55.0)
    assert result.ps_ratio is None
    assert result.ps_percentile is None
    assert result.ps_history_n == 0
    assert any("shares" in f.lower() for f in result.flags)
