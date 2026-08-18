"""Cited fundamental quality scorers over `FundamentalsHistory` (ADR-029 Layer 2).

- Piotroski F-Score (Piotroski 2000): 9-point profitability / leverage / efficiency scorecard.
- Gross profitability (Novy-Marx 2013): gross profit / total assets.
- Financial safety: a leverage + liquidity distress PROXY from available data (a full Altman Z needs
  EBIT + market cap we do not yet pull -- deferred; documented honestly, rule 6).
- QualityScore: a composite carrying the raw components + a standalone [0,1] blend.

All pure and network-free. Missing inputs never award a point (conservative); every score flags
what it could not compute and cites its source. Nothing here predicts -- it flags potential quality.
"""

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division: None if either operand is None or the denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


class FScore(BaseModel):
    """Piotroski (2000) F-Score: the sum of 9 binary financial-health signals (0-9; 8-9 strong,
    0-2 weak). Each component is exposed for legibility; a signal is False when its inputs are
    missing (never award a point on absent data)."""

    model_config = ConfigDict(frozen=True)

    score: int
    roa_positive: bool
    cfo_positive: bool
    delta_roa_positive: bool
    accruals_quality: bool  # CFO/assets > ROA (earnings backed by cash, not accruals)
    delta_leverage_negative: bool
    delta_current_ratio_positive: bool
    no_dilution: bool
    delta_gross_margin_positive: bool
    delta_asset_turnover_positive: bool


class SafetyScore(BaseModel):
    """Leverage/liquidity distress proxy (ADR-029). NOTE: a full Altman Z-Score needs EBIT and
    market capitalization we do not yet pull, so this is a proxy from balance-sheet data only
    (deferred to a later data extension). Lower leverage + higher current ratio + no accumulated
    deficit = safer."""

    model_config = ConfigDict(frozen=True)

    leverage_ratio: float | None  # total liabilities / total assets (lower = safer)
    current_ratio: float | None  # current assets / current liabilities (higher = safer)
    negative_retained_earnings: bool | None  # accumulated deficit -> a distress flag


class QualityScore(BaseModel):
    """Composite fundamental quality (ADR-029), citing Piotroski (2000) + Novy-Marx (2013). Carries
    the raw components and a standalone `score` in [0,1] blending the available legs (F-Score,
    gross profitability, safety). Cross-sectional percentile ranking happens in a later layer;
    here `score` is the single-company blend. `flags` records what could not be computed (rule 6)."""

    model_config = ConfigDict(frozen=True)

    score: float | None
    f_score: FScore
    gross_profitability: float | None
    safety: SafetyScore
    flags: list[str] = []


def piotroski_f_score(history: FundamentalsHistory) -> FScore:
    """Piotroski (2000) F-Score from the two most-recent fiscal years (t = latest, t-1 = prior).
    With fewer than two years, or when a component's inputs are missing, that component scores 0."""
    years: tuple[AnnualFundamentals, ...] = tuple(history.years)
    if len(years) < 2:
        return FScore(
            score=0,
            roa_positive=False,
            cfo_positive=False,
            delta_roa_positive=False,
            accruals_quality=False,
            delta_leverage_negative=False,
            delta_current_ratio_positive=False,
            no_dilution=False,
            delta_gross_margin_positive=False,
            delta_asset_turnover_positive=False,
        )
    t, p = years[-1], years[-2]

    roa_t = _ratio(t.net_income, t.total_assets)
    roa_p = _ratio(p.net_income, p.total_assets)
    cfo_over_assets_t = _ratio(t.operating_cash_flow, t.total_assets)
    lev_t = _ratio(t.long_term_debt, t.total_assets)
    lev_p = _ratio(p.long_term_debt, p.total_assets)
    cr_t = _ratio(t.total_current_assets, t.total_current_liabilities)
    cr_p = _ratio(p.total_current_assets, p.total_current_liabilities)
    gm_t = _ratio(t.gross_profit, t.revenue)
    gm_p = _ratio(p.gross_profit, p.revenue)
    at_t = _ratio(t.revenue, t.total_assets)
    at_p = _ratio(p.revenue, p.total_assets)

    roa_positive = roa_t is not None and roa_t > 0
    cfo_positive = t.operating_cash_flow is not None and t.operating_cash_flow > 0
    delta_roa_positive = roa_t is not None and roa_p is not None and roa_t > roa_p
    accruals_quality = (
        cfo_over_assets_t is not None and roa_t is not None and cfo_over_assets_t > roa_t
    )
    delta_leverage_negative = lev_t is not None and lev_p is not None and lev_t < lev_p
    delta_current_ratio_positive = cr_t is not None and cr_p is not None and cr_t > cr_p
    no_dilution = (
        t.shares_diluted is not None
        and p.shares_diluted is not None
        and t.shares_diluted <= p.shares_diluted
    )
    delta_gross_margin_positive = gm_t is not None and gm_p is not None and gm_t > gm_p
    delta_asset_turnover_positive = at_t is not None and at_p is not None and at_t > at_p

    signals = [
        roa_positive,
        cfo_positive,
        delta_roa_positive,
        accruals_quality,
        delta_leverage_negative,
        delta_current_ratio_positive,
        no_dilution,
        delta_gross_margin_positive,
        delta_asset_turnover_positive,
    ]
    return FScore(
        score=sum(signals),
        roa_positive=roa_positive,
        cfo_positive=cfo_positive,
        delta_roa_positive=delta_roa_positive,
        accruals_quality=accruals_quality,
        delta_leverage_negative=delta_leverage_negative,
        delta_current_ratio_positive=delta_current_ratio_positive,
        no_dilution=no_dilution,
        delta_gross_margin_positive=delta_gross_margin_positive,
        delta_asset_turnover_positive=delta_asset_turnover_positive,
    )


def gross_profitability(history: FundamentalsHistory) -> float | None:
    """Novy-Marx (2013) gross profitability: latest-year gross profit / total assets. The single
    best-known quality signal for future returns; None when either input is missing/zero."""
    if not history.years:
        return None
    latest = history.years[-1]
    return _ratio(latest.gross_profit, latest.total_assets)


def financial_safety(history: FundamentalsHistory) -> SafetyScore:
    """Leverage/liquidity distress proxy from the latest year (ADR-029; a full Altman Z is deferred
    -- it needs EBIT + market cap we do not yet pull). Total liabilities is the accounting identity
    total_assets - total_equity."""
    if not history.years:
        return SafetyScore(leverage_ratio=None, current_ratio=None, negative_retained_earnings=None)
    latest = history.years[-1]
    total_liabilities: float | None = None
    if latest.total_assets is not None and latest.total_equity is not None:
        total_liabilities = latest.total_assets - latest.total_equity
    leverage_ratio = _ratio(total_liabilities, latest.total_assets)
    current_ratio = _ratio(latest.total_current_assets, latest.total_current_liabilities)
    negative_retained_earnings = (
        None if latest.retained_earnings is None else latest.retained_earnings < 0
    )
    return SafetyScore(
        leverage_ratio=leverage_ratio,
        current_ratio=current_ratio,
        negative_retained_earnings=negative_retained_earnings,
    )


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def quality_score(history: FundamentalsHistory) -> QualityScore:
    """Composite fundamental quality (ADR-029): carry the raw F-Score / gross profitability / safety,
    plus a standalone [0,1] `score` = mean of the AVAILABLE normalized legs. A leg with no inputs is
    dropped; the F-Score leg is always available, so `score` is only None if the history is empty."""
    f = piotroski_f_score(history)
    gp = gross_profitability(history)
    safety = financial_safety(history)
    flags: list[str] = []

    legs: list[float] = []
    if history.years:
        legs.append(f.score / 9.0)  # profitability + leverage + efficiency, in [0,1]
    else:
        flags.append("no fundamentals history")

    if gp is not None:
        # profitability rarely exceeds ~50% of assets; map [0, 0.5] -> [0, 1].
        legs.append(_clip(gp, 0.0, 0.5) / 0.5)
    else:
        flags.append("gross profitability unavailable")

    safety_parts: list[float] = []
    if safety.leverage_ratio is not None:
        safety_parts.append(_clip(1.0 - safety.leverage_ratio, 0.0, 1.0))
    if safety.current_ratio is not None:
        safety_parts.append(_clip(safety.current_ratio / 3.0, 0.0, 1.0))
    if safety.negative_retained_earnings is not None:
        safety_parts.append(0.0 if safety.negative_retained_earnings else 1.0)
    if safety_parts:
        legs.append(sum(safety_parts) / len(safety_parts))
    else:
        flags.append("financial safety unavailable")

    score = sum(legs) / len(legs) if legs else None
    return QualityScore(score=score, f_score=f, gross_profitability=gp, safety=safety, flags=flags)
