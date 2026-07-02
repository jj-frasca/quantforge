from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.lab.experiment import Experiment, ExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.search import run_search

FrameProvider = Callable[[str], pd.DataFrame]
FundamentalsProvider = Callable[[str], FundamentalSnapshot | None]


@dataclass(frozen=True)
class UniverseHuntResult:
    experiments: list[Experiment]
    errors: dict[str, str] = field(default_factory=dict)


class LeaderboardRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    deflated_sharpe: float
    graduated: bool
    holdout_sharpe: float | None = None


def run_universe_hunt(
    symbols: list[str],
    strategy_names: list[str],
    frame_provider: FrameProvider,
    *,
    fundamentals_provider: FundamentalsProvider | None = None,
    config: GateConfig | None = None,
    fundamental_criteria: FundamentalCriteria | None = None,
    store: ExperimentStore | None = None,
    n_per_param: int = 3,
    rationale: str = "",
) -> UniverseHuntResult:
    """Hunt across a symbol universe, resiliently. A per-symbol failure (no data, too little
    history, no valid strategies) is recorded in `errors` and skipped; the rest still run. Trial
    counts are per-symbol (via the pool), so a wider universe is more independent shots, not a
    heavier overfitting penalty on any one name.
    """
    experiments: list[Experiment] = []
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            frame = frame_provider(symbol)
            fundamentals = fundamentals_provider(symbol) if fundamentals_provider else None
            prior = store.trials_for_symbol(symbol) if store else 0
            exp = run_search(
                frame,
                symbol,
                strategy_names,
                config=config,
                prior_trials=prior,
                n_per_param=n_per_param,
                fundamentals=fundamentals,
                fundamental_criteria=fundamental_criteria,
                rationale=rationale,
            )
        except (ValueError, KeyError, OSError) as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"
            continue
        if store is not None:
            store.add(exp)
        experiments.append(exp)
    return UniverseHuntResult(experiments=experiments, errors=errors)


def rank_experiments(experiments: list[Experiment]) -> list[LeaderboardRow]:
    """Cross-symbol leaderboard: graduates first, then by best-candidate deflated Sharpe."""
    rows: list[LeaderboardRow] = []
    for exp in experiments:
        if not exp.trials:
            continue
        best = max(exp.trials, key=lambda t: t.deflated_sharpe)
        rows.append(
            LeaderboardRow(
                symbol=exp.symbol,
                strategy_name=best.strategy_name,
                deflated_sharpe=best.deflated_sharpe,
                graduated=exp.graduate is not None,
                holdout_sharpe=exp.graduate.holdout_sharpe if exp.graduate else None,
            )
        )
    return sorted(rows, key=lambda r: (r.graduated, r.deflated_sharpe), reverse=True)
