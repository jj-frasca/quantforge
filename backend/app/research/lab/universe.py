import math
from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.lab.experiment import Experiment, ExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.search import run_search
from app.research.lab.value_filter import ValueGateConfig, ValueProvider, screen_value

_TRADING_DAYS = 252

FrameProvider = Callable[[str], pd.DataFrame]
FundamentalsProvider = Callable[[str], FundamentalSnapshot | None]


@dataclass(frozen=True)
class UniverseHuntResult:
    experiments: list[Experiment]
    errors: dict[str, str] = field(default_factory=dict)
    # Names skipped by the ADR-023 value pre-screen (symbol -> why). Empty when value is off.
    filtered: dict[str, str] = field(default_factory=dict)


class LeaderboardRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    deflated_sharpe: float
    graduated: bool
    holdout_sharpe: float | None = None
    # ADR-018: does the holdout Sharpe clear the best-of-N-under-the-null bar? A far stronger
    # claim than a per-symbol graduate. None for non-graduates.
    survives_universe_deflation: bool | None = None


def expected_max_sharpe_under_null(n_symbols: int, holdout_years: float) -> float:
    """The best annualized holdout Sharpe expected from selecting the best of `n_symbols` under
    the NULL (no skill), given `holdout_years` of data (ADR-018). ~ SE·√(2·ln N), with the
    annualized-Sharpe standard error SE ≈ √(1/T_years) (Lo 2002, higher-Sharpe term dropped for a
    conservative bar). A graduate must clear this to be distinguishable from lucky selection."""
    if n_symbols < 2 or holdout_years <= 0:
        return 0.0
    se = math.sqrt(1.0 / holdout_years)
    return se * math.sqrt(2.0 * math.log(n_symbols))


def run_universe_hunt(
    symbols: list[str],
    strategy_names: list[str],
    frame_provider: FrameProvider,
    *,
    fundamentals_provider: FundamentalsProvider | None = None,
    config: GateConfig | None = None,
    fundamental_criteria: FundamentalCriteria | None = None,
    value_provider: ValueProvider | None = None,
    value_config: ValueGateConfig | None = None,
    store: ExperimentStore | None = None,
    n_per_param: int = 3,
    refine: bool = False,
    refine_span: float = 0.25,
    rationale: str = "",
) -> UniverseHuntResult:
    """Hunt across a symbol universe, resiliently. A per-symbol failure (no data, too little
    history, no valid strategies) is recorded in `errors` and skipped; the rest still run. Trial
    counts are per-symbol (via the pool), so a wider universe is more independent shots, not a
    heavier overfitting penalty on any one name.

    Optional value gate (ADR-023, OFF by default so the existing hunt is unchanged): when a
    `value_provider` is given, each candidate's `UndervaluationScore` is recorded on its Experiment;
    when a `value_config` is ALSO given, names that fail the value pre-screen are skipped (recorded
    in `filtered`) and never hunted. Both are injectable so unit tests use fakes (no network).
    """
    experiments: list[Experiment] = []
    errors: dict[str, str] = {}
    filtered: dict[str, str] = {}
    for symbol in symbols:
        try:
            value_score = value_provider(symbol) if value_provider else None
            if value_provider is not None and value_config is not None:
                screen = screen_value(value_score, value_config)
                if not screen.passed:
                    filtered[symbol] = "; ".join(screen.reasons)
                    continue
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
                refine=refine,
                refine_span=refine_span,
                fundamentals=fundamentals,
                fundamental_criteria=fundamental_criteria,
                rationale=rationale,
            )
        except (ValueError, KeyError, OSError) as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"
            continue
        if value_score is not None:
            exp = exp.model_copy(update={"undervaluation_score": value_score})
        if store is not None:
            store.add(exp)
        experiments.append(exp)
    return UniverseHuntResult(experiments=experiments, errors=errors, filtered=filtered)


def rank_experiments(experiments: list[Experiment]) -> list[LeaderboardRow]:
    """Cross-symbol leaderboard: graduates first, then by best-candidate deflated Sharpe. Each
    graduate is annotated with whether it survives universe-level deflation (ADR-018) — the honest
    cross-symbol test, using the number of symbols searched as the selection breadth."""
    n_symbols = len(experiments)
    rows: list[LeaderboardRow] = []
    for exp in experiments:
        if not exp.trials:
            continue
        best = max(exp.trials, key=lambda t: t.deflated_sharpe)
        survives: bool | None = None
        if exp.graduate is not None:
            holdout_years = exp.graduate.holdout_n_bars / _TRADING_DAYS
            threshold = expected_max_sharpe_under_null(n_symbols, holdout_years)
            survives = exp.graduate.holdout_sharpe > threshold
        rows.append(
            LeaderboardRow(
                symbol=exp.symbol,
                strategy_name=best.strategy_name,
                deflated_sharpe=best.deflated_sharpe,
                graduated=exp.graduate is not None,
                holdout_sharpe=exp.graduate.holdout_sharpe if exp.graduate else None,
                survives_universe_deflation=survives,
            )
        )
    return sorted(rows, key=lambda r: (r.graduated, r.deflated_sharpe), reverse=True)
