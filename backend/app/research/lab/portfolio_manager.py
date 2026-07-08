from collections.abc import Callable
from datetime import datetime

import pandas as pd

from app.research.lab.experiment import Experiment
from app.research.lab.paper import (
    ExitPolicy,
    PaperPosition,
    evaluate_forward,
    evaluate_lifecycle,
    freeze_graduate,
)

FrameProvider = Callable[[str], pd.DataFrame]


def manage_portfolio(
    positions: list[PaperPosition],
    graduate_experiments: list[Experiment],
    frame_provider: FrameProvider,
    *,
    exit_policy: ExitPolicy | None = None,
    now: datetime,
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
        book.append(freeze_graduate(experiment, frozen_at=now))
        held.add(key)

    # Monitor + exit: only OPEN positions; closed ones are left untouched.
    updated: list[PaperPosition] = []
    for position in book:
        if position.status != "open":
            updated.append(position)
            continue
        frame = frame_provider(position.symbol)
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
