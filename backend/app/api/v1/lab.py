from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from app.research.lab.calibration import NullCalibration, PowerSweep
from app.research.lab.experiment import PartitionedExperimentStore
from app.research.lab.paper import JsonFilePaperPortfolio, PaperPosition
from app.research.lab.pool_report import PoolReport, summarize_pool
from app.research.lab.universe import LeaderboardRow, rank_experiments

router = APIRouter(tags=["lab"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_pool_path() -> Path:
    """Path to the research pool directory — one JSON per symbol, ADR-032 (overridable in tests)."""
    return _DATA / "research_pool"


def get_portfolio_path() -> Path:
    """Path to the paper portfolio JSON (overridable in tests)."""
    return _DATA / "paper_portfolio.json"


def get_calibration_path() -> Path:
    """Directory of committed null-model calibrations, one per null mode (overridable in tests)."""
    return _DATA / "null_calibration"


# Sync + read-only: just reads the committed JSON stores (no running hunt, no DB).
@router.get("/leaderboard", response_model=list[LeaderboardRow])
def leaderboard(pool_path: Annotated[Path, Depends(get_pool_path)]) -> list[LeaderboardRow]:
    return rank_experiments(PartitionedExperimentStore(pool_path).all())


@router.get("/paper-portfolio", response_model=list[PaperPosition])
def paper_portfolio(
    portfolio_path: Annotated[Path, Depends(get_portfolio_path)],
) -> list[PaperPosition]:
    return JsonFilePaperPortfolio(portfolio_path).positions()


# Sync + read-only: the ADR-033 honest headline over the same committed JSON stores. Leads with how
# many graduates are distinguishable from best-of-N selection luck, which is the number a reader
# should see before any leaderboard row.
@router.get("/pool-report", response_model=PoolReport)
def pool_report(
    pool_path: Annotated[Path, Depends(get_pool_path)],
    portfolio_path: Annotated[Path, Depends(get_portfolio_path)],
) -> PoolReport:
    return summarize_pool(
        PartitionedExperimentStore(pool_path).all(),
        JsonFilePaperPortfolio(portfolio_path).positions(),
    )


def get_power_calibration_path() -> Path:
    """Directory of committed power sweeps, one per planted process — ADR-053 (overridable)."""
    return _DATA / "power_calibration"


# Sync + read-only: the measured Type-I error of the WHOLE gate (ADR-036/037), written by the
# null-calibration workflow. Returns one row per null mode, or [] when none has been measured —
# an empty list is honest, and a 500 here would take the rest of the dashboard down with it.
@router.get("/null-calibration", response_model=list[NullCalibration])
def null_calibration(
    calibration_path: Annotated[Path, Depends(get_calibration_path)],
) -> list[NullCalibration]:
    if not calibration_path.is_dir():
        return []
    return [
        NullCalibration.model_validate_json(path.read_text())
        for path in sorted(calibration_path.glob("*.json"))
    ]


# Sync + read-only: the measured POWER of the whole gate (ADR-041/042/053), written by the two
# power workflows. Served beside the Type-I error deliberately: a visible false-graduation rate
# with no visible detection rate reads as strength when it is only conservatism.
@router.get("/power-calibration", response_model=list[PowerSweep])
def power_calibration(
    power_calibration_path: Annotated[Path, Depends(get_power_calibration_path)],
) -> list[PowerSweep]:
    if not power_calibration_path.is_dir():
        return []
    return [
        PowerSweep.model_validate_json(path.read_text())
        for path in sorted(power_calibration_path.glob("*.json"))
    ]
