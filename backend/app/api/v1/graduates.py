from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.research.lab.experiment import PartitionedExperimentStore
from app.research.lab.universe import rank_experiments

router = APIRouter(tags=["graduates"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_pool_path() -> Path:
    """Path to the research pool directory — one JSON per symbol, ADR-032 (overridable in tests)."""
    return _DATA / "research_pool"


class GraduateRow(BaseModel):
    """One strategy that cleared the graduation gate — the headline "it survived" view. A projection
    of the leaderboard restricted to graduates, so `graduated` is dropped (always true here) and the
    universe-deflation verdict is surfaced as the honest cross-symbol-selection caveat (ADR-018)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    deflated_sharpe: float
    holdout_sharpe: float | None = None
    survives_universe_deflation: bool | None = None
    undervaluation_score: float | None = None


# Sync + read-only: reranks the committed pool and keeps only its graduates (no hunt, no DB).
@router.get("/graduates", response_model=list[GraduateRow])
def graduates(pool_path: Annotated[Path, Depends(get_pool_path)]) -> list[GraduateRow]:
    rows = rank_experiments(PartitionedExperimentStore(pool_path).all())
    # rank_experiments already orders graduates first, by deflated Sharpe descending, so filtering
    # preserves best-first order.
    return [
        GraduateRow(
            symbol=row.symbol,
            strategy_name=row.strategy_name,
            deflated_sharpe=row.deflated_sharpe,
            holdout_sharpe=row.holdout_sharpe,
            survives_universe_deflation=row.survives_universe_deflation,
            undervaluation_score=row.undervaluation_score,
        )
        for row in rows
        if row.graduated
    ]
