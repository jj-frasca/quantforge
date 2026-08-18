"""Hard financial-distress screen (ADR-029 Layer 3c): a business-quality safety rail on top of the
statistical gate. A name that is genuinely near-insolvent must not graduate a strategy into the
paper book no matter how good its backtest looks.

A full Altman Z-Score (the classic distress model) needs EBIT + market capitalization we do not yet
pull (deferred, ADR-029), so this is a conservative balance-sheet + cash-flow PROXY. It is tuned for
HIGH PRECISION on purpose: a false veto kills a real edge, so distress requires BOTH chronic
operating weakness (unprofitable AND burning operating cash) AND a balance-sheet failure (insolvent
OR illiquid). Negative equity ALONE is not distress — buyback-heavy blue chips (MCD, SBUX, HD) run
negative book equity while thriving. Missing inputs never veto (an unscorable name graduates on
technicals, exactly like the ADR-017 fundamentals fallback). Flags potential distress (rule 6)."""

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory
from app.research.fundamentals.quality import financial_safety


class DistressScreen(BaseModel):
    """Whether the latest filing shows hard financial distress, with a reason per tripped signal.
    Flags a name as *potentially* distressed (rule 6); it never asserts insolvency."""

    model_config = ConfigDict(frozen=True)

    distressed: bool
    reasons: list[str] = []


def financial_distress(history: FundamentalsHistory) -> DistressScreen:
    """Screen the latest year for hard distress. Distress = (negative net income AND negative
    operating cash flow) AND (liabilities exceed assets OR current ratio < 1). Any missing input
    fails its own signal, so an under-reported name simply cannot be judged distressed."""
    if not history.years:
        return DistressScreen(distressed=False, reasons=[])
    latest = history.years[-1]
    safety = financial_safety(history)

    unprofitable = latest.net_income is not None and latest.net_income < 0
    burning_cash = latest.operating_cash_flow is not None and latest.operating_cash_flow < 0
    insolvent = safety.leverage_ratio is not None and safety.leverage_ratio > 1.0
    illiquid = safety.current_ratio is not None and safety.current_ratio < 1.0

    if not (unprofitable and burning_cash and (insolvent or illiquid)):
        return DistressScreen(distressed=False, reasons=[])

    reasons = ["negative net income", "negative operating cash flow"]
    if insolvent:
        reasons.append("liabilities exceed assets (negative equity)")
    if illiquid:
        reasons.append("current ratio < 1 (cannot cover short-term liabilities)")
    return DistressScreen(distressed=True, reasons=reasons)
