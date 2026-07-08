from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.paper import JsonFilePaperPortfolio, PaperPosition
from app.research.lab.universe import LeaderboardRow, rank_experiments

router = APIRouter(tags=["lab"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_pool_path() -> Path:
    """Path to the research pool JSON (overridable in tests)."""
    return _DATA / "research_pool.json"


def get_portfolio_path() -> Path:
    """Path to the paper portfolio JSON (overridable in tests)."""
    return _DATA / "paper_portfolio.json"


# Sync + read-only: just reads the committed JSON stores (no running hunt, no DB).
@router.get("/leaderboard", response_model=list[LeaderboardRow])
def leaderboard(pool_path: Annotated[Path, Depends(get_pool_path)]) -> list[LeaderboardRow]:
    return rank_experiments(JsonFileExperimentStore(pool_path).all())


@router.get("/paper-portfolio", response_model=list[PaperPosition])
def paper_portfolio(
    portfolio_path: Annotated[Path, Depends(get_portfolio_path)],
) -> list[PaperPosition]:
    return JsonFilePaperPortfolio(portfolio_path).positions()
