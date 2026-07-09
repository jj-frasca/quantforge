"""Value pre-screen for the hunt (ADR-023).

Combines the technical algo with *genuinely undervalued* companies: a tunable, versioned,
OFF-by-default filter that keeps only names whose `UndervaluationScore` looks cheap, and a provider
that composes the ADR-022 contract (`fetch_history` → `price_join` → `score_valuation`) into a
per-symbol score. Names that cannot be scored (ETFs / unmapped tickers) pass through on technicals
only, exactly like the ADR-017 fundamentals veto. Honest per rule 6 — it flags a name as
*potentially* (not) undervalued, never asserts it.
"""

from collections.abc import Callable, Sequence
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory
from app.research.backtesting.manifest import compute_parameter_hash
from app.research.valuation import UndervaluationScore, score_valuation
from app.research.valuation.intrinsic_value import DcfAssumptions
from app.research.valuation.price_join import attach_fiscal_year_prices

ValueProvider = Callable[[str], UndervaluationScore | None]
HistoryProvider = Callable[[str], FundamentalsHistory]
PriceSeriesProvider = Callable[[str], Sequence[tuple[date, float]]]


class ValueGateConfig(BaseModel):
    """Versioned, tunable value pre-screen thresholds (ADR-023), mirroring `GateConfig`. Recorded
    with every run so a filtered universe is reproducible against the exact rubric that judged it.
    """

    model_config = ConfigDict(frozen=True)

    # Cheapness score is 0-1 (higher = cheaper vs own P/E+P/S history + DCF margin of safety), so a
    # name passes when its score >= min_score. 0.5 is the neutral midpoint — a permissive starting
    # point, a calibration knob (like GateConfig), not a proven constant.
    min_score: float = 0.5
    # A name we cannot score (ETF / no CIK / no computable components) passes and is hunted on
    # technicals only — the ADR-017 fallback generalized. Set False for a fundamentals-required run.
    keep_unscored: bool = True
    # Optional stricter gate: also require a positive DCF margin of safety. Off by default — the DCF
    # is the most assumption-laden signal (ADR-022).
    require_margin_of_safety: bool = False

    @property
    def version_hash(self) -> str:
        return compute_parameter_hash(self.model_dump())


class ValueScreen(BaseModel):
    """Whether a name clears the value pre-screen, with the score it was judged on and a reason per
    failed check. Flags a name as *potentially* (not) undervalued (rule 6)."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    score: float | None
    reasons: list[str] = []


def screen_value(score: UndervaluationScore | None, config: ValueGateConfig) -> ValueScreen:
    """Decide whether ``score`` clears the pre-screen. A missing score (None object, or a scored
    object whose composite is uncomputable) routes through ``keep_unscored`` — never vetoed for
    being unscorable, only optionally excluded."""
    composite = score.score if score is not None else None
    if score is None or composite is None:
        unscored_reasons = (
            []
            if config.keep_unscored
            else ["no undervaluation score available (fundamentals not scorable)"]
        )
        return ValueScreen(passed=config.keep_unscored, score=None, reasons=unscored_reasons)

    reasons: list[str] = []
    if composite < config.min_score:
        reasons.append(
            f"undervaluation score {composite:.2f} < {config.min_score:.2f} "
            "(not cheap enough vs its own history + intrinsic value)"
        )
    if config.require_margin_of_safety:
        mos = score.margin_of_safety
        if mos is None or mos <= 0.0:
            reasons.append("no positive margin of safety vs DCF intrinsic value")
    return ValueScreen(passed=not reasons, score=composite, reasons=reasons)


def make_value_provider(
    history_provider: HistoryProvider,
    price_series_provider: PriceSeriesProvider,
    *,
    assumptions: DcfAssumptions | None = None,
) -> ValueProvider:
    """Compose the ADR-022 contract into a per-symbol `UndervaluationScore` provider: fetch the
    fundamentals history, join a market price onto each fiscal-year end (`price_join`), and score
    at the current (last) close. Both providers are injected, so unit tests use fakes (no network
    in CI) and a `@pytest.mark.live` test wires `SecEdgarFundamentalsSource.fetch_history` + a real
    price series. A name whose history lookup raises (ETF / unmapped ticker) or that has no prices
    yields None (unscored → technicals only)."""

    def provide(symbol: str) -> UndervaluationScore | None:
        try:
            history = history_provider(symbol)
        except (ValueError, KeyError, OSError):
            return None
        closes = list(price_series_provider(symbol))
        if not closes:
            return None
        joined = attach_fiscal_year_prices(history, closes)
        current_price = closes[-1][1]
        return score_valuation(joined, current_price, assumptions=assumptions)

    return provide
