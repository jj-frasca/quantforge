from dataclasses import dataclass

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

    Notes:
        A strategy whose Sharpe swings wildly with small parameter changes is likely overfit.
        stability_score = 1 / (1 + CV) where CV is the coefficient of variation of Sharpe
        across configs — 1.0 when identical, falling toward 0 as dispersion grows. Heuristic,
        not a guarantee.
    """
    if len(sharpes) < 2:
        raise ValueError("need >= 2 configurations")

    arr = np.asarray(sharpes, dtype=np.float64)
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
