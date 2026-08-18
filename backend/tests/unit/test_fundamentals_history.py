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
    include_balance_sheet: bool = True,
    gross_profit_mode: str = "direct",  # "direct" GrossProfit tag / "derive" COGS only / "none"
    long_term_debt_tag: str = "LongTermDebtNoncurrent",
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
    if include_balance_sheet:
        gaap["Assets"] = {
            "units": {
                "USD": [_fact(200_000 + 10_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
        gaap["AssetsCurrent"] = {
            "units": {
                "USD": [_fact(50_000 + 5_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
        gaap["LiabilitiesCurrent"] = {
            "units": {
                "USD": [_fact(30_000 + 2_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
        gaap[long_term_debt_tag] = {
            "units": {"USD": [_fact(40_000, fy, f"a-{fy}") for fy in years]}
        }
        gaap["RetainedEarningsAccumulatedDeficit"] = {
            "units": {
                "USD": [_fact(70_000 + 5_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
        gaap["StockholdersEquity"] = {
            "units": {
                "USD": [_fact(90_000 + 5_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
    if gross_profit_mode == "direct":
        gaap["GrossProfit"] = {
            "units": {
                "USD": [_fact(60_000 + 5_000 * i, fy, f"a-{fy}") for i, fy in enumerate(years)]
            }
        }
    elif gross_profit_mode == "derive":
        # No GrossProfit tag; COGS lets the parser derive gross_profit = revenue - COGS.
        gaap["CostOfGoodsAndServicesSold"] = {
            "units": {"USD": [_fact(50_000, fy, f"a-{fy}") for fy in years]}
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


def test_history_records_fiscal_period_end_date_for_the_price_join() -> None:
    from datetime import date

    hist = parse_company_facts_history(_facts(), "AAPL")
    # _fact sets the period end to <fy>-09-30 — the anchor the price join uses.
    assert hist.years[-1].period_end == date(2024, 9, 30)
    assert hist.years[0].period_end == date(2022, 9, 30)


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


def test_history_parses_balance_sheet_and_cashflow_line_items() -> None:
    # Quality factors (ADR-029) need the balance-sheet + cash-flow line items per year.
    hist = parse_company_facts_history(_facts(), "AAPL")
    latest = hist.years[-1]  # fy 2024, i=2
    assert latest.total_assets == 220_000
    assert latest.total_current_assets == 60_000
    assert latest.total_current_liabilities == 34_000
    assert latest.long_term_debt == 40_000
    assert latest.gross_profit == 70_000  # direct GrossProfit tag
    assert latest.operating_cash_flow == 36_000
    assert latest.retained_earnings == 80_000
    assert latest.total_equity == 100_000


def test_missing_balance_sheet_tags_leave_new_fields_none() -> None:
    # Resilience: a filer that omits these tags yields None per field, never an error.
    hist = parse_company_facts_history(
        _facts(include_balance_sheet=False, include_cashflow=False, gross_profit_mode="none"),
        "AAPL",
    )
    for y in hist.years:
        assert y.total_assets is None
        assert y.total_current_assets is None
        assert y.total_current_liabilities is None
        assert y.long_term_debt is None
        assert y.gross_profit is None
        assert y.operating_cash_flow is None
        assert y.retained_earnings is None
        assert y.total_equity is None
    assert hist.years[-1].revenue == 120_000  # existing line items still present


def test_gross_profit_derived_from_revenue_minus_cogs_when_tag_absent() -> None:
    hist = parse_company_facts_history(_facts(gross_profit_mode="derive"), "AAPL")
    latest = hist.years[-1]
    # revenue 120_000 - COGS 50_000 = 70_000
    assert latest.gross_profit == 70_000


def test_gross_profit_none_when_neither_gross_profit_nor_cogs_present() -> None:
    hist = parse_company_facts_history(_facts(gross_profit_mode="none"), "AAPL")
    assert all(y.gross_profit is None for y in hist.years)


def test_long_term_debt_falls_back_to_secondary_tag() -> None:
    hist = parse_company_facts_history(_facts(long_term_debt_tag="LongTermDebt"), "AAPL")
    assert hist.years[-1].long_term_debt == 40_000


def test_operating_cash_flow_exposed_even_without_capex() -> None:
    # operating_cash_flow stands on its own tag, independent of FCF's capex leg.
    hist = parse_company_facts_history(_facts(), "AAPL")
    assert [y.operating_cash_flow for y in hist.years] == [30_000, 33_000, 36_000]
