"""Composite undervaluation score (ADR-022).

Blends the peer-free signals — where the current P/E and P/S sit within the company's own
history, and the DCF margin of safety — into a single 0-1 score, cited to the latest 10-K.
A low own-history percentile and a positive margin of safety push the score up. Only the
*available* components are averaged; every missing input becomes a flag, never a silent default.
Honest per rule 6: it flags a company as *potentially* undervalued, never asserts it is.
"""

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.multiples import compute_multiples


class UndervaluationScore(BaseModel):
    """How undervalued a company looks versus its own history + intrinsic value, cited (rule 6)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    cik: int
    entity_name: str
    fiscal_year: int
    form: str
    accession_number: str
    source_url: str
    source: str = "SEC EDGAR"

    current_price: float

    pe_ratio: float | None
    pe_percentile: float | None
    ps_ratio: float | None
    ps_percentile: float | None

    intrinsic_value_per_share: float | None
    margin_of_safety: float | None
    growth_rate_used: float | None
    fcf_is_net_income_proxy: bool

    score: float | None
    flags: list[str]


def score_valuation(
    history: FundamentalsHistory,
    price: float,
    *,
    assumptions: DcfAssumptions | None = None,
) -> UndervaluationScore:
    """Score how undervalued ``history``'s company looks at ``price``. ``score`` is the mean of the
    available components — cheapness vs own P/E history, vs own P/S history, and margin of safety
    (each in [0, 1], cheap = high) — or None when no component is computable."""
    multiples = compute_multiples(history, price)
    intrinsic = dcf_intrinsic_value(history, assumptions)
    latest = history.years[-1]

    ivps = intrinsic.intrinsic_value_per_share
    margin_of_safety = (ivps - price) / ivps if ivps is not None and ivps > 0 else None

    components: list[float] = []
    if multiples.pe_percentile is not None:
        components.append(1.0 - multiples.pe_percentile)
    if multiples.ps_percentile is not None:
        components.append(1.0 - multiples.ps_percentile)
    if margin_of_safety is not None:
        components.append(min(max(margin_of_safety, 0.0), 1.0))

    score = sum(components) / len(components) if components else None
    flags = [*multiples.flags, *intrinsic.flags]
    if score is None:
        flags.append("no valuation components available — cannot score")

    return UndervaluationScore(
        symbol=history.symbol,
        cik=history.cik,
        entity_name=history.entity_name,
        fiscal_year=latest.fiscal_year,
        form=history.form,
        accession_number=history.accession_number,
        source_url=history.source_url,
        current_price=price,
        pe_ratio=multiples.pe_ratio,
        pe_percentile=multiples.pe_percentile,
        ps_ratio=multiples.ps_ratio,
        ps_percentile=multiples.ps_percentile,
        intrinsic_value_per_share=ivps,
        margin_of_safety=margin_of_safety,
        growth_rate_used=intrinsic.growth_rate_used,
        fcf_is_net_income_proxy=intrinsic.fcf_is_net_income_proxy,
        score=score,
        flags=flags,
    )
