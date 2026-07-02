from typing import Any

from pydantic import BaseModel, ConfigDict

# Ordered GAAP tag fallbacks per concept — filer tag usage varies (ADR-017). First hit wins.
_REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
_NET_INCOME_TAGS = ("NetIncomeLoss",)
_GROSS_PROFIT_TAGS = ("GrossProfit",)
_EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")


class FundamentalSnapshot(BaseModel):
    """Point-in-time fundamentals for a symbol, each figure traceable to a specific SEC filing
    (ADR-017). Reports what the filer stated — never a claim of correctness (rule 6)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    cik: int
    entity_name: str
    fiscal_year: int
    form: str
    accession_number: str
    source_url: str
    source: str = "SEC EDGAR"

    revenue: float
    revenue_growth_yoy: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    eps: float | None = None
    pe_ratio: float | None = None  # None until joined with a market price


def _annual_facts(
    gaap: dict[str, Any], tags: tuple[str, ...], unit: str = "USD"
) -> list[dict[str, Any]]:
    """Annual (10-K, full-year) datapoints for the first matching tag, oldest→newest by fiscal
    year. Empty if no tag matches. Deduped to one value per fiscal year (latest filing wins)."""
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        rows = node.get("units", {}).get(unit, [])
        annual = [
            r for r in rows if r.get("fp") == "FY" and str(r.get("form", "")).startswith("10-K")
        ]
        if not annual:
            continue
        by_year: dict[int, dict[str, Any]] = {}
        for row in sorted(annual, key=lambda r: r.get("filed", "")):
            by_year[int(row["fy"])] = row  # later filed overwrites -> latest restatement wins
        return [by_year[fy] for fy in sorted(by_year)]
    return []


def parse_company_facts(company_facts: dict[str, Any], symbol: str) -> FundamentalSnapshot:
    """Parse an EDGAR CompanyFacts payload into a FundamentalSnapshot for the latest fiscal year.

    Raises ValueError if no annual revenue facts are present (revenue anchors margins + growth).
    """
    cik = int(company_facts.get("cik", 0))
    entity_name = str(company_facts.get("entityName", symbol))
    gaap = company_facts.get("facts", {}).get("us-gaap", {})

    revenue_rows = _annual_facts(gaap, _REVENUE_TAGS)
    if not revenue_rows:
        raise ValueError(f"no annual revenue facts found for {symbol!r}")
    latest = revenue_rows[-1]
    fiscal_year = int(latest["fy"])
    revenue = float(latest["val"])

    revenue_growth_yoy: float | None = None
    if len(revenue_rows) >= 2:
        prior = float(revenue_rows[-2]["val"])
        if prior != 0.0:
            revenue_growth_yoy = (revenue - prior) / abs(prior)

    def _latest_value_for_year(tags: tuple[str, ...], unit: str = "USD") -> float | None:
        rows = _annual_facts(gaap, tags, unit)
        for row in rows:
            if int(row["fy"]) == fiscal_year:
                return float(row["val"])
        return None

    net_income = _latest_value_for_year(_NET_INCOME_TAGS)
    gross_profit = _latest_value_for_year(_GROSS_PROFIT_TAGS)
    eps = _latest_value_for_year(_EPS_TAGS, unit="USD/shares")

    net_margin = net_income / revenue if net_income is not None and revenue != 0.0 else None
    gross_margin = gross_profit / revenue if gross_profit is not None and revenue != 0.0 else None

    accession = str(latest["accn"])
    return FundamentalSnapshot(
        symbol=symbol,
        cik=cik,
        entity_name=entity_name,
        fiscal_year=fiscal_year,
        form=str(latest["form"]),
        accession_number=accession,
        source_url=(
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
            f"&type=10-K&accession_number={accession}"
        ),
        revenue=revenue,
        revenue_growth_yoy=revenue_growth_yoy,
        gross_margin=gross_margin,
        net_margin=net_margin,
        eps=eps,
    )
