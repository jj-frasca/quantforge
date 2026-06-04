"""Generate validation config grids from the catalog (ADR-010 §Consequences).

Notes:
    /validate runs PBO, walk-forward, etc. over a *grid* of strategy configurations;
    historically each grid was hand-curated per strategy. Hand-curated grids drift the
    moment a new strategy lands (the same drift mode the catalog was meant to prevent
    [[ADR-010]]), so this module derives the grid mechanically from the catalog's
    ParamSchema.

    Generation strategy:
    - For each tunable parameter, take `n_per_param` evenly-spaced values in
      `[minimum, maximum]` from the catalog. Bounds default to a wide window around
      the default if the catalog leaves them open.
    - Take the Cartesian product → a raw grid of (name, params) candidates.
    - Build each candidate via `build_strategy_from_dict`; SKIP combinations that fail
      Pydantic validation OR the strategy constructor's cross-parameter rules
      (e.g. SMA's `fast < slow`, RSI's `oversold < overbought`). Constraint-violating
      points in the grid are silently dropped — the alternative is to encode every
      cross-parameter rule in the catalog, which couples the schema to the algorithms.

    The discarded points reduce the effective grid size; the caller should request
    enough perturbations that the survivors meet the §8 minimum for PBO/CSCV (>= 2
    valid configs; ~6+ recommended).
"""

import itertools

import numpy as np
from pydantic import ValidationError

from app.research.strategies.base import BaseStrategy
from app.research.strategies.builder import build_strategy_from_dict
from app.research.strategies.catalog import STRATEGY_CATALOG, ParamSchema, StrategySchema


def find_catalog_entry(name: str) -> StrategySchema | None:
    return next((entry for entry in STRATEGY_CATALOG if entry.name == name), None)


def _values_for_param(param: ParamSchema, n: int) -> list[float | int]:
    """`n` evenly-spaced values in the catalog's [minimum, maximum] for one parameter.

    Notes:
        Falls back to `default * [0.5, 1.5]` when bounds are missing. Coerces back to
        int when the catalog declared the parameter as `int` (linspace yields floats).
    """
    if n < 1:
        raise ValueError("n_per_param must be >= 1")
    if n == 1:
        return [param.default]

    low = param.minimum if param.minimum is not None else param.default * 0.5
    high = param.maximum if param.maximum is not None else param.default * 1.5
    raw: list[float] = np.linspace(low, high, n).tolist()

    if param.type == "int":
        # Round, de-duplicate, sort. Rounding can collapse two endpoints (e.g. linspace
        # over [1, 2] with n=3 -> [1.0, 1.5, 2.0] -> [1, 2, 2] -> [1, 2]).
        # round() on a single arg returns int (PEP 3141), so no int() cast needed.
        ints: list[int] = sorted({round(v) for v in raw})
        return list(ints)
    return list(raw)


def grid_from_catalog(entry: StrategySchema, n_per_param: int = 3) -> list[BaseStrategy]:
    """Cartesian product of catalog-driven perturbations, filtered to valid strategies.

    Returns concrete `BaseStrategy` instances; the caller doesn't need to know about
    the (name, params) intermediate form.
    """
    per_param_values = [_values_for_param(p, n_per_param) for p in entry.parameters]
    strategies: list[BaseStrategy] = []
    for combo in itertools.product(*per_param_values):
        params = {p.name: v for p, v in zip(entry.parameters, combo, strict=True)}
        try:
            strategies.append(build_strategy_from_dict(entry.name, params))
        except (ValidationError, ValueError):
            # Cross-parameter constraint violation (fast >= slow, oversold >= overbought,
            # ...). Skip and continue — the surviving grid is the validation grid.
            continue
    return strategies
