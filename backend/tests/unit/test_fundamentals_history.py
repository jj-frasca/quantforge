"""Parse an EDGAR CompanyFacts payload into a multi-year FundamentalsHistory (ADR-022).
Additive to the latest-year FundamentalSnapshot parser; fixture-based, no network."""

import pytest

from app.data.fundamentals import (
    AnnualFundamentals,
    FundamentalsHistory,
    parse_company_facts_history,
)


def _fact(val: float, fy: int, accn: str, *, form: str = "10-K", fp: str = "FY") -> dict:
    return {
        "end": f"{fy}-09-30",
        "val": val,
        "fy": fy,
        "fp": fp,
        "form": form,
        "accn": accn,
        "filed": f"{fy + 1}-02-01",
    }


def _facts(
    *,
    years: tuple[int, ...] = (2022, 2023, 2024),
    include_shares: bool = True,
    include_cashflow: bool = True,
) -> dict:
    rev = {
        "units": {"USD": [_fact(100_000 + 10_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]}
    }
    ni = {
        "units": {"USD": [_fact(20_000 + 2_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]}
    }
    eps = {"units": {"USD/shares": [_fact(5.0 + i, fy, f"a-{fy}") for i, fy in enumerate(years)]}}
    gaap: dict = {
        "Revenues": rev,
        "NetIncomeLoss": ni,
        "EarningsPerShareDiluted": eps,
    }
    if include_shares:
        gaap["WeightedAverageNumberOfDilutedSharesOutstanding"] = {
            "units": {"shares": [_fact(4_000, fy, f"a-{fy}") for fy in years]}
        }
    if include_cashflow:
        gaap["NetCashProvidedByUsedInOperatingActivities"] = {
            "units": {
                "USD": [_fact(30_000 + 3_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
        gaap["PaymentsToAcquirePropertyPlantAndEquipment"] = {
            "units": {"USD": [_fact(5_000, fy, f"a-{fy}") for fy in years]}
        }
    return {"cik": 320193, "entityName": "Apple Inc.", "facts": {"us-gaap": gaap}}


def test_history_has_one_ordered_record_per_fiscal_year() -> None:
    hist = parse_company_facts_history(_facts(), "AAPL")
    assert isinstance(hist, FundamentalsHistory)
    assert [y.fiscal_year for y in hist.years] == [2022, 2023, 2024]
    assert all(isinstance(y, AnnualFundamentals) for y in hist.years)


def test_history_pulls_line_items_and_derives_fcf() -> None:
    hist = parse_company_facts_history(_facts(), "AAPL")
    latest = hist.years[-1]
    assert latest.revenue == 120_000
    assert latest.net_income == 24_000
    assert latest.eps == 7.0
    assert latest.shares_diluted == 4_000
    # FCF = operating cash flow - capex
    assert latest.free_cash_flow == 36_000 - 5_000
    assert latest.price is None  # EDGAR carries no market price


def test_history_carries_citation_of_latest_filing() -> None:
    hist = parse_company_facts_history(_facts(), "AAPL")
    assert hist.symbol == "AAPL"
    assert hist.cik == 320193
    assert hist.entity_name == "Apple Inc."
    assert hist.form == "10-K"
    assert hist.accession_number == "a-2024"
    assert "320193" in hist.source_url
    assert hist.source == "SEC EDGAR"


def test_missing_cashflow_tags_leave_fcf_none() -> None:
    hist = parse_company_facts_history(_facts(include_cashflow=False), "AAPL")
    assert all(y.free_cash_flow is None for y in hist.years)
    assert hist.years[-1].net_income == 24_000  # other line items still present


def test_missing_shares_leaves_shares_none() -> None:
    hist = parse_company_facts_history(_facts(include_shares=False), "AAPL")
    assert all(y.shares_diluted is None for y in hist.years)


def test_no_revenue_facts_raises() -> None:
    empty = {"cik": 1, "entityName": "X", "facts": {"us-gaap": {}}}
    with pytest.raises(ValueError, match="revenue"):
        parse_company_facts_history(empty, "X")


def test_history_round_trips_json() -> None:
    hist = parse_company_facts_history(_facts(), "AAPL")
    assert FundamentalsHistory.model_validate_json(hist.model_dump_json()) == hist
