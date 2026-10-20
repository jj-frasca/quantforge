from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.research.cross_sectional.purged import PurgedDiagnostic
from app.research.cross_sectional.search import CrossSectionalExperiment
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.trial_counts import require_trial_count

router = APIRouter(tags=["cross-sectional"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_pool_path() -> Path:
    """Path to the cross-sectional pool JSON (overridable in tests)."""
    return _DATA / "cross_sectional_pool.json"


class CrossSectionalTrialView(BaseModel):
    """One strategy's finalist in a cross-sectional hunt — the ranking metrics the dashboard shows."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    strategy_name: str
    observed_sharpe: float
    deflated_sharpe: float
    pbo: float
    parameter_stability_score: float
    # Rank IC (ADR-035) — did the RANKING carry information, as opposed to a couple of names
    # carrying the P&L. None for trials recorded before ADR-035: not measured, not zero.
    ic_mean: float | None = None
    ic_t_stat: float | None = None
    walk_forward_oos_sharpe: float | None = Field(default=None, allow_inf_nan=False)
    purged_cv_oos_sharpe: float | None = Field(default=None, allow_inf_nan=False)
    purged_diagnostic: PurgedDiagnostic | None = None

    @model_validator(mode="after")
    def _validate_purged_evidence(self) -> "CrossSectionalTrialView":
        evidence = self.purged_diagnostic
        if evidence is None:
            return self
        expected = evidence.mean_oos_sharpe if evidence.status == "measured" else None
        if self.purged_cv_oos_sharpe != expected:
            raise ValueError("trial purged scalar must match current evidence status and mean")
        return self


class CrossSectionalView(BaseModel):
    """The latest cross-sectional hunt (ADR-024): its per-strategy trials, graduation verdict, and
    universe size. A per-strategy/universe record, not per-symbol — so it stands apart from the
    single-name leaderboard."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    created_at: datetime
    universe_size: int
    best_strategy_name: str | None
    graduated: bool
    graduate_holdout_sharpe: float | None
    trials: list[CrossSectionalTrialView]
    # ADR-322: publish compact stored evidence, never infer attribution for legacy scalars.
    walk_forward_method: Literal["family-walk-forward-equal-weight-continuation-v1"] | None = None
    walk_forward_hold_sharpe: float | None = Field(default=None, allow_inf_nan=False)
    walk_forward_n_bars: int | None = None
    walk_forward_n_splits: int | None = None

    @field_validator("walk_forward_n_bars", "walk_forward_n_splits", mode="before")
    @classmethod
    def _validate_walk_forward_count(cls, value: object) -> int | None:
        if value is None:
            return None
        return require_trial_count(value, minimum=1, parameter="walk_forward geometry")

    @model_validator(mode="after")
    def _validate_walk_forward_evidence(self) -> "CrossSectionalView":
        evidence = (
            self.walk_forward_hold_sharpe,
            self.walk_forward_n_bars,
            self.walk_forward_n_splits,
        )
        if self.walk_forward_method is None:
            if any(value is not None for value in evidence):
                raise ValueError("walk-forward pairing and geometry require a method")
            return self
        if not self.trials or any(trial.walk_forward_oos_sharpe is None for trial in self.trials):
            raise ValueError("measured walk-forward requires every family mean and nonempty trials")
        if (
            self.walk_forward_hold_sharpe is None
            or self.walk_forward_n_bars is None
            or self.walk_forward_n_splits is None
        ):
            raise ValueError("measured walk-forward requires paired benchmark and geometry")
        if self.walk_forward_n_bars < self.walk_forward_n_splits + 1:
            raise ValueError("walk-forward bars must be >= splits + 1")
        return self

    @model_validator(mode="after")
    def _validate_purged_evidence(self) -> "CrossSectionalView":
        evidence = [trial.purged_diagnostic for trial in self.trials]
        if not any(item is not None for item in evidence):
            return self
        if any(item is None for item in evidence):
            raise ValueError("current purged evidence requires every family outcome")
        first = evidence[0]
        assert first is not None
        request = (first.method, first.n_bars, first.requested_folds, first.floor)
        for item in evidence:
            assert item is not None
            if (item.method, item.n_bars, item.requested_folds, item.floor) != request:
                raise ValueError("purged families must carry the same request geometry")
            if self.walk_forward_method is not None and item.n_bars != self.walk_forward_n_bars:
                raise ValueError("purged bars must match attributed walk-forward bars")
        return self


def _view(experiment: CrossSectionalExperiment) -> CrossSectionalView:
    experiment = CrossSectionalExperiment.model_validate(experiment.model_dump(round_trip=True))
    return CrossSectionalView(
        created_at=experiment.created_at,
        universe_size=len(experiment.universe_symbols),
        best_strategy_name=experiment.best_strategy_name,
        graduated=experiment.graduate is not None,
        graduate_holdout_sharpe=(
            experiment.graduate.holdout_sharpe if experiment.graduate else None
        ),
        walk_forward_method=experiment.walk_forward_method,
        walk_forward_hold_sharpe=experiment.walk_forward_hold_sharpe,
        walk_forward_n_bars=experiment.walk_forward_n_bars,
        walk_forward_n_splits=experiment.walk_forward_n_splits,
        trials=[
            CrossSectionalTrialView(
                strategy_name=t.strategy_name,
                observed_sharpe=t.observed_sharpe,
                deflated_sharpe=t.deflated_sharpe,
                pbo=t.pbo,
                parameter_stability_score=t.parameter_stability_score,
                ic_mean=t.ic.mean if t.ic else None,
                ic_t_stat=t.ic.t_stat if t.ic else None,
                walk_forward_oos_sharpe=t.walk_forward_oos_sharpe,
                purged_cv_oos_sharpe=t.purged_cv_oos_sharpe,
                purged_diagnostic=t.purged_diagnostic,
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
