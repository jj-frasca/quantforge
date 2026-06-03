from fastapi import APIRouter

from app.research.strategies.catalog import STRATEGY_CATALOG, StrategySchema

router = APIRouter(tags=["strategies"])


@router.get("/strategies", response_model=list[StrategySchema])
def list_strategies() -> list[StrategySchema]:
    """Return the strategy catalog — what's available and what each takes.

    Drives the frontend strategy dropdown + the per-strategy parameter form.
    Adding a strategy means editing STRATEGY_CATALOG (and the matching Pydantic
    config); the frontend renders the new option automatically.
    """
    return STRATEGY_CATALOG
