"""Parse SEC EDGAR CompanyFacts JSON into a citation-carrying FundamentalSnapshot (ADR-017).
Pure + deterministic — fixture-based, no network (the live pull is a @pytest.mark.live test)."""

import pytest

from app.data.fundamentals import FundamentalSnapshot, parse_company_facts


def _usd_fact(val: float, fy: int, accn: str, end: str) -> dict:
    return {
        "end": end,
        "val": val,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "accn": accn,
        "filed": f"{fy + 1}-02-01",
    }


def _facts(
    *, revenue_tag: str = "Revenues", include_gross: bool = True, two_years: bool = True
) -> dict:
    rev = [_usd_fact(400_000, 2024, "0000320193-25-000001", "2024-09-30")]
    ni = [_usd_fact(100_000, 2024, "0000320193-25-000001", "2024-09-30")]
    gp = [_usd_fact(180_000, 2024, "0000320193-25-000001", "2024-09-30")]
    eps = [
        {
            "end": "2024-09-30",
            "val": 6.5,
            "fy": 2024,
            "fp": "FY",
            "form": "10-K",
            "accn": "0000320193-25-000001",
            "filed": "2025-02-01",
        }
    ]
    if two_years:
        rev.insert(0, _usd_fact(350_000, 2023, "0000320193-24-000001", "2023-09-30"))
        ni.insert(0, _usd_fact(90_000, 2023, "0000320193-24-000001", "2023-09-30"))
    gaap: dict = {
        revenue_tag: {"units": {"USD": rev}},
        "NetIncomeLoss": {"units": {"USD": ni}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
    }
    if include_gross:
        gaap["GrossProfit"] = {"units": {"USD": gp}}
    return {"cik": 320193, "entityName": "Apple Inc.", "facts": {"us-gaap": gaap}}


def test_parses_latest_year_metrics_and_citation() -> None:
    snap = parse_company_facts(_facts(), "AAPL")
    assert isinstance(snap, FundamentalSnapshot)
    assert snap.symbol == "AAPL"
    assert snap.cik == 320193
    assert snap.fiscal_year == 2024
    assert snap.revenue == 400_000
    assert snap.revenue_growth_yoy == pytest.approx((400_000 - 350_000) / 350_000)
    assert snap.net_margin == pytest.approx(100_000 / 400_000)
    assert snap.gross_margin == pytest.approx(180_000 / 400_000)
    assert snap.eps == 6.5
    # Citation points at the specific 10-K.
    assert snap.form == "10-K"
    assert snap.accession_number == "0000320193-25-000001"
    assert snap.source == "SEC EDGAR"
    assert "320193" in snap.source_url


def test_revenue_tag_fallback_when_primary_tag_absent() -> None:
    snap = parse_company_facts(
        _facts(revenue_tag="RevenueFromContractWithCustomerExcludingAssessedTax"), "AAPL"
    )
    assert snap.revenue == 400_000


def test_missing_prior_year_leaves_growth_none() -> None:
    snap = parse_company_facts(_facts(two_years=False), "AAPL")
    assert snap.revenue == 400_000
    assert snap.revenue_growth_yoy is None


def test_missing_gross_profit_leaves_gross_margin_none() -> None:
    snap = parse_company_facts(_facts(include_gross=False), "AAPL")
    assert snap.gross_margin is None
    assert snap.net_margin is not None  # net still computable


def test_tag_with_only_quarterly_rows_falls_through_to_next_tag() -> None:
    # "Revenues" exists but carries only a 10-Q row (no annual) -> the parser must skip it and
    # fall through to the next candidate tag ("SalesRevenueNet") that has the 10-K figure.
    facts = {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 90_000,
                                "fy": 2024,
                                "fp": "Q3",
                                "form": "10-Q",
                                "accn": "q",
                                "filed": "2024-08-01",
                                "end": "2024-06-30",
                            }
                        ]
                    }
                },
                "SalesRevenueNet": {
                    "units": {"USD": [_usd_fact(400_000, 2024, "a", "2024-09-30")]}
                },
                "NetIncomeLoss": {"units": {"USD": [_usd_fact(100_000, 2024, "a", "2024-09-30")]}},
            }
        },
    }
    snap = parse_company_facts(facts, "AAPL")
    assert snap.revenue == 400_000


def test_no_revenue_facts_raises() -> None:
    empty = {"cik": 1, "entityName": "X", "facts": {"us-gaap": {}}}
    with pytest.raises(ValueError):
        parse_company_facts(empty, "X")


def test_snapshot_round_trips_json() -> None:
    snap = parse_company_facts(_facts(), "AAPL")
    assert FundamentalSnapshot.model_validate_json(snap.model_dump_json()) == snap
