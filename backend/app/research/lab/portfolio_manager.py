from collections.abc import Callable
from datetime import datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.lab.experiment import Experiment
from app.research.lab.paper import (
    ExitPolicy,
    PaperPosition,
    evaluate_forward,
    evaluate_lifecycle,
    freeze_graduate,
)

FrameProvider = Callable[[str], pd.DataFrame]


def newly_promoted(before: list[PaperPosition], after: list[PaperPosition]) -> list[PaperPosition]:
    """The positions in `after` whose (symbol, strategy_name) was not in `before` — i.e. the
    graduates freshly promoted into the managed book this step. Lets the discovery consolidation
    report which NEW strategies just cleared the gate (visibility into what is working)."""
    prior = {(p.symbol, p.strategy_name) for p in before}
    return [p for p in after if (p.symbol, p.strategy_name) not in prior]


class DeflationCohorts(BaseModel):
    """The paper book split by the ADR-018 universe-deflation verdict recorded at promotion
    (ADR-033). The honest headline for any book summary: how many of these positions are actually
    distinguishable from best-of-N selection luck, and are those the ones performing forward?

    Positions whose verdict is unknown (frozen before ADR-033, or from a single-symbol run) are
    counted separately and excluded from both means — fabricating a control group out of missing
    metadata would be worse than reporting less."""

    model_config = ConfigDict(frozen=True)

    n_survivors: int
    n_non_survivors: int
    n_unknown: int
    survivor_mean_forward_sharpe: float | None = None
    non_survivor_mean_forward_sharpe: float | None = None


def _mean_forward_sharpe(positions: list[PaperPosition]) -> float | None:
    scored = [p.score.forward_sharpe for p in positions if p.score is not None]
    return sum(scored) / len(scored) if scored else None


def deflation_cohorts(positions: list[PaperPosition]) -> DeflationCohorts:
    """Summarize `positions` by their recorded universe-deflation verdict (ADR-033)."""
    survivors = [p for p in positions if p.survives_universe_deflation is True]
    non_survivors = [p for p in positions if p.survives_universe_deflation is False]
    unknown = [p for p in positions if p.survives_universe_deflation is None]
    return DeflationCohorts(
        n_survivors=len(survivors),
        n_non_survivors=len(non_survivors),
        n_unknown=len(unknown),
        survivor_mean_forward_sharpe=_mean_forward_sharpe(survivors),
        non_survivor_mean_forward_sharpe=_mean_forward_sharpe(non_survivors),
    )


def manage_portfolio(
    positions: list[PaperPosition],
    graduate_experiments: list[Experiment],
    frame_provider: FrameProvider,
    *,
    exit_policy: ExitPolicy | None = None,
    now: datetime,
    universe_n_symbols: int | None = None,
) -> list[PaperPosition]:
    """Advance the managed paper book one step (ADR-020): PROMOTE new graduates, MONITOR every open
    position, and EXIT the deteriorating ones. Closed positions are kept as an honest record and a
    cut name is not re-promoted. Pure over `frame_provider` (injectable → testable without network).
    """
    policy = exit_policy or ExitPolicy()

    # Promote: freeze any graduate we don't already hold (open OR previously closed — a cut loser
    # is not re-added).
    held = {(p.symbol, p.strategy_name) for p in positions}
    book = list(positions)
    for experiment in graduate_experiments:
        if experiment.graduate is None:
            continue
        key = (experiment.symbol, experiment.graduate.strategy_name)
        if key in held:
            continue
        book.append(
            freeze_graduate(experiment, frozen_at=now, universe_n_symbols=universe_n_symbols)
        )
        held.add(key)

    # Monitor + exit: only OPEN positions; closed ones are left untouched.
    updated: list[PaperPosition] = []
    for position in book:
        if position.status != "open":
            updated.append(position)
            continue
        try:
            frame = frame_provider(position.symbol)
        except (ValueError, KeyError, OSError, ArithmeticError, TypeError):
            # A per-position data fetch failure (flaky yfinance: no data, or a malformed bar that
            # makes the OHLCV normalizer raise decimal.InvalidOperation) must not crash the whole
            # managed book — leave this position unchanged this cycle and keep monitoring the rest
            # (prod 2026-08-04; same class of failure the hunts already guard against).
            updated.append(position)
            continue
        score = evaluate_forward(position, frame)
        decision = evaluate_lifecycle(position, frame, policy)
        if decision.action == "exit":
            updated.append(
                position.model_copy(
                    update={
                        "status": "closed",
                        "closed_at": now,
                        "exit_reasons": decision.reasons,
                        "score": score,
                    }
                )
            )
        else:
            updated.append(position.model_copy(update={"score": score}))
    return updated
