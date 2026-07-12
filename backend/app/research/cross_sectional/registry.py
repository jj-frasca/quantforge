from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pandas as pd

from app.research.cross_sectional.strategies import (
    momentum_signal,
    reversal_signal,
    value_signal,
)

SignalFn = Callable[[pd.DataFrame], pd.DataFrame]
Params = dict[str, float | int]


@dataclass(frozen=True)
class CrossSectionalStrategy:
    """A cross-sectional strategy: a name, a factory that binds a parameter combo into a
    prices->signal-panel function, and the grid of signal-parameter combos to search over. The
    portfolio-construction quantile is orthogonal (applied in the engine), so the search multiplies
    this grid by its quantile grid — every strategy therefore has >= 2 configs for PBO."""

    name: str
    build: Callable[[Params], SignalFn]
    param_grid: tuple[Params, ...]


def default_strategies(
    value_scores: Mapping[str, float] | None = None,
) -> dict[str, CrossSectionalStrategy]:
    """The shipped cross-sectional strategies (ADR-024). Momentum + reversal are price-only and
    always present; value is included only when an UndervaluationScore map is supplied (an
    unscored universe cannot rank on value)."""
    strategies: dict[str, CrossSectionalStrategy] = {
        "xs_momentum": CrossSectionalStrategy(
            name="xs_momentum",
            build=lambda p: (
                lambda prices: momentum_signal(prices, int(p["lookback"]), int(p["skip"]))
            ),
            param_grid=tuple(
                {"lookback": lb, "skip": sk} for lb in (126, 189, 252) for sk in (0, 21)
            ),
        ),
        "xs_reversal": CrossSectionalStrategy(
            name="xs_reversal",
            build=lambda p: lambda prices: reversal_signal(prices, int(p["lookback"])),
            param_grid=tuple({"lookback": lb} for lb in (3, 5, 10)),
        ),
    }
    if value_scores is not None:
        strategies["xs_value"] = CrossSectionalStrategy(
            name="xs_value",
            build=lambda p: lambda prices: value_signal(prices, value_scores),
            param_grid=({},),
        )
    return strategies
