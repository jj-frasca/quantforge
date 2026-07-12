from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.lab.experiment import ExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.paper import ExitPolicy, PaperPosition
from app.research.lab.portfolio_manager import manage_portfolio
from app.research.lab.universe import UniverseHuntResult, run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, ValueProvider

FrameProvider = Callable[[str], pd.DataFrame]
FundamentalsProvider = Callable[[str], FundamentalSnapshot | None]


class PaperPortfolio(Protocol):
    def positions(self) -> list[PaperPosition]: ...
    def save(self, positions: list[PaperPosition]) -> None: ...


@dataclass(frozen=True)
class ScheduledHuntResult:
    hunt: UniverseHuntResult
    positions: list[PaperPosition]  # the full managed book after this step
    promoted: list[PaperPosition]  # names newly frozen as OPEN positions this step


def hunt_and_promote(
    symbols: list[str],
    strategy_names: list[str],
    frame_provider: FrameProvider,
    *,
    pool: ExperimentStore,
    portfolio: PaperPortfolio,
    fundamentals_provider: FundamentalsProvider | None = None,
    config: GateConfig | None = None,
    fundamental_criteria: FundamentalCriteria | None = None,
    value_provider: ValueProvider | None = None,
    value_config: ValueGateConfig | None = None,
    exit_policy: ExitPolicy | None = None,
    now: datetime,
    refine: bool = True,
    rationale: str = "",
) -> ScheduledHuntResult:
    """Scheduled mass-test → auto-promotion (WP-F, builds on ADR-020). Run the universe hunt
    (accumulating every experiment in the pool → the per-symbol DSR/MinTRL trial flywheel), then
    hand ALL pool graduates to the managed portfolio (WP-A): a graduate we don't already hold is
    frozen as an OPEN position; open positions are monitored and exited if they deteriorate.

    Notes:
        Promotion draws from the whole pool, not just this run's graduates, so a graduate from an
        earlier hunt that was never promoted is still picked up (idempotent — a held or previously
        cut name is not re-added). Pure over its providers/stores → unit-testable without network.
        A `value_provider` (ADR-023, WP-J) records a cited `UndervaluationScore` on each hunted
        name; a `value_config` additionally pre-screens out names below min_score — both forwarded
        straight to the hunt (record-first: recording on, the hard gate opt-in).
    """
    hunt = run_universe_hunt(
        symbols,
        strategy_names,
        frame_provider,
        fundamentals_provider=fundamentals_provider,
        config=config,
        fundamental_criteria=fundamental_criteria,
        value_provider=value_provider,
        value_config=value_config,
        store=pool,
        refine=refine,
        rationale=rationale,
    )
    graduates = [e for e in pool.all() if e.graduate is not None]
    before = {(p.symbol, p.strategy_name) for p in portfolio.positions()}
    updated = manage_portfolio(
        portfolio.positions(), graduates, frame_provider, exit_policy=exit_policy, now=now
    )
    portfolio.save(updated)
    promoted = [p for p in updated if (p.symbol, p.strategy_name) not in before]
    return ScheduledHuntResult(hunt=hunt, positions=updated, promoted=promoted)
