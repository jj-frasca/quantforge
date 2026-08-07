from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pandas as pd

from app.research.cross_sectional.strategies import (
    alpha19_signal,
    alpha34_signal,
    composite_signal,
    high_proximity_signal,
    low_volatility_signal,
    momentum_signal,
    residual_momentum_signal,
    reversal_signal,
    risk_adjusted_momentum_signal,
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
        "xs_low_volatility": CrossSectionalStrategy(
            name="xs_low_volatility",
            build=lambda p: lambda prices: low_volatility_signal(prices, int(p["vol_window"])),
            param_grid=tuple({"vol_window": vw} for vw in (21, 63, 126)),
        ),
        "xs_short_term_reversal_1m": CrossSectionalStrategy(
            name="xs_short_term_reversal_1m",
            build=lambda p: lambda prices: reversal_signal(prices, int(p["lookback"])),
            param_grid=tuple({"lookback": lb} for lb in (21, 42, 63)),
        ),
        "xs_52w_high": CrossSectionalStrategy(
            name="xs_52w_high",
            build=lambda p: lambda prices: high_proximity_signal(prices, int(p["window"])),
            param_grid=tuple({"window": w} for w in (126, 189, 252)),
        ),
        "xs_residual_momentum": CrossSectionalStrategy(
            name="xs_residual_momentum",
            build=lambda p: (
                lambda prices: residual_momentum_signal(
                    prices, int(p["lookback"]), int(p["skip"]), int(p["mean_window"])
                )
            ),
            param_grid=tuple(
                {"lookback": lb, "skip": 21, "mean_window": 60} for lb in (126, 189, 252)
            ),
        ),
        "xs_risk_adjusted_momentum": CrossSectionalStrategy(
            name="xs_risk_adjusted_momentum",
            build=lambda p: (
                lambda prices: risk_adjusted_momentum_signal(prices, int(p["lookback"]))
            ),
            param_grid=tuple({"lookback": lb} for lb in (63, 126, 252)),
        ),
        "xs_composite": CrossSectionalStrategy(
            name="xs_composite",
            build=lambda p: lambda prices: composite_signal(prices, int(p["lookback"])),
            param_grid=tuple({"lookback": lb} for lb in (63, 126, 252)),
        ),
        "xs_alpha34": CrossSectionalStrategy(
            name="xs_alpha34",
            build=lambda p: (
                lambda prices: alpha34_signal(prices, int(p["short_window"]), int(p["long_window"]))
            ),
            param_grid=tuple(
                {"short_window": sw, "long_window": lw} for sw, lw in ((2, 5), (3, 10), (5, 20))
            ),
        ),
        "xs_alpha19": CrossSectionalStrategy(
            name="xs_alpha19",
            build=lambda p: lambda prices: alpha19_signal(prices, int(p["change_lag"])),
            param_grid=tuple({"change_lag": cl} for cl in (7, 14, 21)),
        ),
    }
    if value_scores is not None:
        strategies["xs_value"] = CrossSectionalStrategy(
            name="xs_value",
            build=lambda p: lambda prices: value_signal(prices, value_scores),
            param_grid=({},),
        )
    return strategies
