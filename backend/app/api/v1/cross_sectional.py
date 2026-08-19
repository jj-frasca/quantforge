from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.research.cross_sectional.search import CrossSectionalExperiment
from app.research.cross_sectional.store import JsonFileCrossSectionalStore

router = APIRouter(tags=["cross-sectional"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_pool_path() -> Path:
    """Path to the cross-sectional pool JSON (overridable in tests)."""
    return _DATA / "cross_sectional_pool.json"


class CrossSectionalTrialView(BaseModel):
    """One strategy's finalist in a cross-sectional hunt — the ranking metrics the dashboard shows."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    observed_sharpe: float
    deflated_sharpe: float
    pbo: float
    parameter_stability_score: float
    # Rank IC (ADR-035) — did the RANKING carry information, as opposed to a couple of names
    # carrying the P&L. None for trials recorded before ADR-035: not measured, not zero.
    ic_mean: float | None = None
    ic_t_stat: float | None = None


class CrossSectionalView(BaseModel):
    """The latest cross-sectional hunt (ADR-024): its per-strategy trials, graduation verdict, and
    universe size. A per-strategy/universe record, not per-symbol — so it stands apart from the
    single-name leaderboard."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    universe_size: int
    best_strategy_name: str | None
    graduated: bool
    graduate_holdout_sharpe: float | None
    trials: list[CrossSectionalTrialView]


def _view(experiment: CrossSectionalExperiment) -> CrossSectionalView:
    return CrossSectionalView(
        created_at=experiment.created_at,
        universe_size=len(experiment.universe_symbols),
        best_strategy_name=experiment.best_strategy_name,
        graduated=experiment.graduate is not None,
        graduate_holdout_sharpe=(
            experiment.graduate.holdout_sharpe if experiment.graduate else None
        ),
        trials=[
            CrossSectionalTrialView(
                strategy_name=t.strategy_name,
                observed_sharpe=t.observed_sharpe,
                deflated_sharpe=t.deflated_sharpe,
                pbo=t.pbo,
                parameter_stability_score=t.parameter_stability_score,
                ic_mean=t.ic.mean if t.ic else None,
                ic_t_stat=t.ic.t_stat if t.ic else None,
            )
            for t in experiment.trials
        ],
    )


# Sync + read-only: reads the committed cross-sectional pool (no hunt, no DB). An empty/missing pool
# is a normal answer (no hunt has produced a record yet) → null, never a 500.
@router.get("/cross-sectional", response_model=CrossSectionalView | None)
def cross_sectional(
    pool_path: Annotated[Path, Depends(get_pool_path)],
) -> CrossSectionalView | None:
    experiments = JsonFileCrossSectionalStore(pool_path).all()
    if not experiments:
        return None
    return _view(max(experiments, key=lambda e: e.created_at))
