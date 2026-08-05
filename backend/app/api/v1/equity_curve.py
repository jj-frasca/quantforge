"""Read-only equity-curve endpoint: the headline "are we making money?" view over the paper account.
Returns the committed EquityPoint snapshots oldest-first (as recorded). Mirrors the graduates endpoint
— reads the committed JSON series with a dependency-injected path so tests feed a synthetic file and
an empty/missing file is a normal answer (`[]`), never a 500."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from app.execution.equity_curve import EquityPoint, JsonFileEquityCurve

router = APIRouter(tags=["equity-curve"])

_DATA = Path(__file__).resolve().parents[3].parent / "data"


def get_equity_curve_path() -> Path:
    """Path to the committed paper equity-curve JSON (overridable in tests)."""
    return _DATA / "equity_curve.json"


# Sync + read-only: reads the committed equity-curve series (no broker, no DB). The series is written
# oldest-first (each broker run appends), so file order is chronological — returned as-is.
@router.get("/equity-curve", response_model=list[EquityPoint])
def equity_curve(path: Annotated[Path, Depends(get_equity_curve_path)]) -> list[EquityPoint]:
    return JsonFileEquityCurve(path).all()
