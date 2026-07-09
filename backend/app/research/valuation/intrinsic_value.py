"""Absolute intrinsic value via a simple FCFE DCF (ADR-022).

Projects a base free cash flow at a clamped, history-derived growth rate for a fixed horizon,
adds a Gordon-growth terminal value, discounts at the cost of equity, and divides by diluted
shares. It discounts *equity* free cash flow directly, so it ignores a separate net-debt bridge
(a disclosed simplification, ADR-022). Every fallback is flagged; the assumptions are recorded
on the result. Honest per rule 6 — it flags a *potential* value, never asserts fair value.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from app.data.fundamentals import FundamentalsHistory


class DcfAssumptions(BaseModel):
    """Tunable, disclosed DCF knobs. ``discount_rate`` must exceed ``terminal_growth`` or the
    Gordon terminal value diverges."""

    model_config = ConfigDict(frozen=True)

    discount_rate: float = 0.10
    terminal_growth: float = 0.025
    projection_years: int = 5
    max_growth: float = 0.12
    min_growth: float = 0.0

    @model_validator(mode="after")
    def _discount_exceeds_terminal(self) -> "DcfAssumptions":
        if self.discount_rate <= self.terminal_growth:
            raise ValueError("discount_rate must exceed terminal_growth (Gordon TV diverges)")
        return self


class IntrinsicValueResult(BaseModel):
    """DCF outcome, carrying the inputs used so the number is auditable (rule 6)."""

    model_config = ConfigDict(frozen=True)

    intrinsic_value_per_share: float | None
    growth_rate_used: float | None
    fcf_base: float | None
    fcf_is_net_income_proxy: bool
    assumptions: DcfAssumptions
    flags: list[str]


def _cagr(values: Sequence[float | None]) -> float | None:
    """Compound annual growth of a fully-present, all-positive oldest→newest series (len ≥ 2)."""
    if len(values) < 2 or any(v is None or v <= 0 for v in values):
        return None
    first, last = values[0], values[-1]
    assert first is not None and last is not None  # narrowed by the guard above
    growth: float = (last / first) ** (1 / (len(values) - 1)) - 1
    return growth


def estimate_growth(history: FundamentalsHistory) -> float | None:
    """History-derived growth: CAGR of FCF, else net income, else revenue. None if none qualify."""
    for series in (
        [y.free_cash_flow for y in history.years],
        [y.net_income for y in history.years],
        [y.revenue for y in history.years],
    ):
        growth = _cagr(series)
        if growth is not None:
            return growth
    return None


def dcf_intrinsic_value(
    history: FundamentalsHistory, assumptions: DcfAssumptions | None = None
) -> IntrinsicValueResult:
    """Intrinsic value per share for the latest fiscal year. Returns a result with a None value
    and an explanatory flag whenever the DCF is not meaningful (missing/non-positive inputs)."""
    a = assumptions or DcfAssumptions()
    latest = history.years[-1]
    flags: list[str] = []

    base = latest.free_cash_flow
    is_proxy = False
    if base is None:
        base = latest.net_income
        is_proxy = base is not None
        if is_proxy:
            flags.append("free cash flow unavailable — used net income as a proxy")

    def _fail(reason: str, *, fcf_base: float | None) -> IntrinsicValueResult:
        flags.append(reason)
        return IntrinsicValueResult(
            intrinsic_value_per_share=None,
            growth_rate_used=None,
            fcf_base=fcf_base,
            fcf_is_net_income_proxy=is_proxy,
            assumptions=a,
            flags=flags,
        )

    if base is None:
        return _fail("no free cash flow or net income to value", fcf_base=None)
    if base <= 0:
        return _fail("non-positive base cash flow — DCF not meaningful", fcf_base=base)
    shares = latest.shares_diluted
    if shares is None or shares <= 0:
        return _fail("shares outstanding unavailable — cannot value per share", fcf_base=base)

    growth = estimate_growth(history)
    if growth is None:
        growth = a.terminal_growth
        flags.append("growth unavailable from history — used terminal growth")
    growth = min(max(growth, a.min_growth), a.max_growth)

    r, gt, n = a.discount_rate, a.terminal_growth, a.projection_years
    equity_value = 0.0
    fcf_t = base
    for t in range(1, n + 1):
        fcf_t = base * (1 + growth) ** t
        equity_value += fcf_t / (1 + r) ** t
    terminal_value = fcf_t * (1 + gt) / (r - gt)
    equity_value += terminal_value / (1 + r) ** n

    return IntrinsicValueResult(
        intrinsic_value_per_share=equity_value / shares,
        growth_rate_used=growth,
        fcf_base=base,
        fcf_is_net_income_proxy=is_proxy,
        assumptions=a,
        flags=flags,
    )
