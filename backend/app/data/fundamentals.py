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
_SHARES_TAGS = (
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
)
_OCF_TAGS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
_CAPEX_TAGS = ("PaymentsToAcquirePropertyPlantAndEquipment",)


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


class AnnualFundamentals(BaseModel):
    """One fiscal year of line items for a symbol (ADR-022). ``price`` is the market price near
    the fiscal-year end, joined from the price layer upstream — EDGAR carries no prices."""

    model_config = ConfigDict(frozen=True)

    fiscal_year: int
    revenue: float
    net_income: float | None = None
    eps: float | None = None
    shares_diluted: float | None = None
    free_cash_flow: float | None = None
    price: float | None = None


class FundamentalsHistory(BaseModel):
    """Multi-year fundamentals for a symbol, oldest→newest, cited to the latest 10-K (ADR-022).
    Reports what the filer stated — never a claim of correctness (rule 6)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    cik: int
    entity_name: str
    form: str
    accession_number: str
    source_url: str
    source: str = "SEC EDGAR"

    years: tuple[AnnualFundamentals, ...]


class FundamentalCriteria(BaseModel):
    """Tunable 'sane fundamentals' thresholds (ADR-017). A None threshold skips that check."""

    model_config = ConfigDict(frozen=True)

    min_revenue_growth_yoy: float | None = 0.0
    min_net_margin: float | None = 0.0


class FundamentalScreen(BaseModel):
    """Whether a name's fundamentals clear the criteria, with a reason per failed check."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    reasons: list[str] = []


def screen_fundamentals(
    snapshot: FundamentalSnapshot, criteria: FundamentalCriteria
) -> FundamentalScreen:
    """Conservative screen: a metric we cannot verify (None) FAILS its check — we don't trade a
    company whose fundamentals we can't confirm."""
    reasons: list[str] = []
    if criteria.min_revenue_growth_yoy is not None:
        g = snapshot.revenue_growth_yoy
        if g is None:
            reasons.append("revenue growth unavailable (cannot verify)")
        elif g < criteria.min_revenue_growth_yoy:
            reasons.append(f"revenue growth {g:.1%} < {criteria.min_revenue_growth_yoy:.1%}")
    if criteria.min_net_margin is not None:
        m = snapshot.net_margin
        if m is None:
            reasons.append("net margin unavailable (cannot verify)")
        elif m < criteria.min_net_margin:
            reasons.append(f"net margin {m:.1%} < {criteria.min_net_margin:.1%}")
    return FundamentalScreen(passed=not reasons, reasons=reasons)


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


def _year_value_map(
    gaap: dict[str, Any], tags: tuple[str, ...], unit: str = "USD"
) -> dict[int, float]:
    """Fiscal-year → value for the first matching tag. Empty if no tag matches."""
    return {int(row["fy"]): float(row["val"]) for row in _annual_facts(gaap, tags, unit)}


def parse_company_facts_history(company_facts: dict[str, Any], symbol: str) -> FundamentalsHistory:
    """Parse an EDGAR CompanyFacts payload into a multi-year FundamentalsHistory (ADR-022).

    Revenue anchors the set of fiscal years; other line items are joined per year where present.
    Raises ValueError if no annual revenue facts exist.
    """
    cik = int(company_facts.get("cik", 0))
    entity_name = str(company_facts.get("entityName", symbol))
    gaap = company_facts.get("facts", {}).get("us-gaap", {})

    revenue_rows = _annual_facts(gaap, _REVENUE_TAGS)
    if not revenue_rows:
        raise ValueError(f"no annual revenue facts found for {symbol!r}")

    revenue_by_year = {int(row["fy"]): float(row["val"]) for row in revenue_rows}
    net_income = _year_value_map(gaap, _NET_INCOME_TAGS)
    eps = _year_value_map(gaap, _EPS_TAGS, unit="USD/shares")
    shares = _year_value_map(gaap, _SHARES_TAGS, unit="shares")
    ocf = _year_value_map(gaap, _OCF_TAGS)
    capex = _year_value_map(gaap, _CAPEX_TAGS)

    years: list[AnnualFundamentals] = []
    for fy in sorted(revenue_by_year):
        cash_from_ops, capital_spend = ocf.get(fy), capex.get(fy)
        fcf = (
            cash_from_ops - capital_spend
            if cash_from_ops is not None and capital_spend is not None
            else None
        )
        years.append(
            AnnualFundamentals(
                fiscal_year=fy,
                revenue=revenue_by_year[fy],
                net_income=net_income.get(fy),
                eps=eps.get(fy),
                shares_diluted=shares.get(fy),
                free_cash_flow=fcf,
            )
        )

    latest = revenue_rows[-1]
    accession = str(latest["accn"])
    return FundamentalsHistory(
        symbol=symbol,
        cik=cik,
        entity_name=entity_name,
        form=str(latest["form"]),
        accession_number=accession,
        source_url=(
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
            f"&type=10-K&accession_number={accession}"
        ),
        years=tuple(years),
    )
