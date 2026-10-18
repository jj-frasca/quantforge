import math
from dataclasses import dataclass
from numbers import Real

import numpy as np


@dataclass(frozen=True)
class ParameterStability:
    mean_sharpe: float
    std_sharpe: float
    min_sharpe: float
    max_sharpe: float
    fraction_profitable: float
    stability_score: float  # in [0, 1]; higher = less sensitive to the parameter choice


def parameter_stability(sharpes: list[float]) -> ParameterStability:
    """Summarize how robust performance is across a parameter grid.

    Original observations must be nonboolean real scalars with finite Float64
    inspection, and converted evidence must be one-dimensional. Decimal and
    coercible non-real objects are unsupported. Native reduction arithmetic
    and finite projection precision are not certified by these input guards.

    Notes:
        A strategy whose Sharpe swings wildly with small parameter changes is likely overfit.
        stability_score = 1 / (1 + CV) where CV is the coefficient of variation of Sharpe
        across configs — 1.0 when identical, falling toward 0 as dispersion grows. Heuristic,
        not a guarantee.
    """
    if len(sharpes) < 2:
        raise ValueError("need >= 2 configurations")

    for value in sharpes:
        score: object = value
        if isinstance(score, (bool, np.bool_)) or not isinstance(score, Real):
            raise ValueError("Sharpe observations must be finite real nonboolean scalars")
        try:
            inspected = float(score)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Sharpe observations must be finite real scalars") from exc
        if not math.isfinite(inspected):
            raise ValueError("Sharpe observations must be finite real scalars")

    arr = np.asarray(sharpes, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("Sharpe observations must be one-dimensional")
    mean = float(arr.mean())
    std = float(arr.std(ddof=1))
    cv = std / (abs(mean) + 1e-9)
    return ParameterStability(
        mean_sharpe=mean,
        std_sharpe=std,
        min_sharpe=float(arr.min()),
        max_sharpe=float(arr.max()),
        fraction_profitable=float((arr > 0).mean()),
        stability_score=float(np.clip(1.0 / (1.0 + cv), 0.0, 1.0)),
    )
