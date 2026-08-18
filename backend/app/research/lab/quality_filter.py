"""Business-quality pre-screen for the hunt (ADR-029 §4b).

The honest way to make the ADR-018 universe-deflation bar clearable is to test **fewer, better-
motivated hypotheses** — not to lower the bar. ADR-033 explicitly refuses to shrink N by declaring
correlated names "not independent"; screening the universe on an ex-ante, economically motivated
quality criterion is the legitimate alternative, because it genuinely reduces the number of
hypotheses tested rather than re-describing the same number of them.

That only holds if the rubric is fixed **in advance**. `QualityGateConfig` is versioned and recorded
with the run for exactly that reason: a filtered universe must be reproducible against the rubric
that judged it, and tuning the screen until graduates appear would be the very thing charter §4
forbids.

Scores come from the ADR-029 fundamentals pool (one EDGAR sweep per week), not from a per-symbol
fetch at hunt time. A name the sweep never scored — an ETF, an unmapped ticker — passes through on
technicals only, exactly like the ADR-017 fundamentals veto and the ADR-023 value screen. Honest per
rule 6: this flags a name as *potentially* low-quality; it never asserts it.

OFF by default. Wiring it into a scheduled hunt is a separate, evidence-based decision.
"""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from app.research.backtesting.manifest import compute_parameter_hash
from app.research.fundamentals.record import FundamentalRecord

QualityProvider = Callable[[str], FundamentalRecord | None]


class QualityGateConfig(BaseModel):
    """Versioned, tunable quality pre-screen thresholds (ADR-029 4b), mirroring `ValueGateConfig`."""

    model_config = ConfigDict(frozen=True)

    # Composite quality is 0-1 (F-score + gross profitability + financial safety). 0.5 is the
    # neutral midpoint — a permissive starting point and a calibration knob, not a proven constant.
    min_quality_score: float = 0.5
    # Optional Piotroski floor. Off by default: the composite already includes the F-score, so this
    # is a second, stricter gate for a run that wants a hard balance-sheet requirement.
    min_f_score: int | None = None
    # A name the EDGAR sweep never scored (ETF / no CIK) passes and is hunted on technicals only.
    # Set False for a fundamentals-required run.
    keep_unscored: bool = True

    @property
    def version_hash(self) -> str:
        return compute_parameter_hash(self.model_dump())


class QualityScreen(BaseModel):
    """Whether a name clears the quality pre-screen, with the score it was judged on and a reason
    per failed check. Flags a name as *potentially* low-quality (rule 6)."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    score: float | None
    reasons: list[str] = []


def screen_quality(record: FundamentalRecord | None, config: QualityGateConfig) -> QualityScreen:
    """Decide whether `record` clears the pre-screen. A missing record, or one whose composite is
    uncomputable, routes through `keep_unscored` — never vetoed for being unscorable."""
    score = record.quality_score if record is not None else None
    if score is None:
        reasons = [] if config.keep_unscored else ["no quality score available (not in the pool)"]
        return QualityScreen(passed=config.keep_unscored, score=None, reasons=reasons)

    failures: list[str] = []
    if score < config.min_quality_score:
        failures.append(
            f"quality score {score:.2f} < {config.min_quality_score:.2f} "
            "(weak profitability / balance sheet vs the rubric)"
        )
    if (
        record is not None
        and config.min_f_score is not None
        and record.f_score < config.min_f_score
    ):
        failures.append(f"Piotroski F-score {record.f_score} < {config.min_f_score}")
    return QualityScreen(passed=not failures, score=score, reasons=failures)


def make_quality_provider(records: list[FundamentalRecord]) -> QualityProvider:
    """Index the ADR-029 fundamentals pool by symbol. A symbol filed under several fiscal years
    keeps the NEWEST — the same newest-wins rule `merge_fundamental_records` applies by CIK, so the
    screen judges a name on its latest filing rather than whichever row happened to come last."""
    by_symbol: dict[str, FundamentalRecord] = {}
    for record in records:
        key = record.symbol.upper()
        current = by_symbol.get(key)
        if current is None or record.fiscal_year > current.fiscal_year:
            by_symbol[key] = record

    def provide(symbol: str) -> FundamentalRecord | None:
        return by_symbol.get(symbol.upper())

    return provide
