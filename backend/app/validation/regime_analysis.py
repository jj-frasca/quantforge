from dataclasses import dataclass

import pandas as pd

from app.research.backtesting.metrics import sharpe_ratio


@dataclass(frozen=True)
class RegimeMetrics:
    n_bars: int
    total_return: float
    sharpe: float


def analyze_regimes(
    strategy_returns: pd.Series, market_prices: pd.Series, window: int = 20
) -> dict[str, RegimeMetrics]:
    """Break a strategy's performance down by market regime (validation-methodology.md §5).

    Notes:
        Each bar is labelled by the sign of the market's trailing ``window`` return: "bull"
        (>= 0, also the warmup default) or "bear" (< 0). A strategy that only works in one
        regime is fragile. Regimes partition every bar exactly once.
    """
    strat, market = strategy_returns.align(market_prices, join="inner")
    trailing = market.pct_change(window)
    regime = pd.Series("bull", index=strat.index)
    regime[trailing < 0] = "bear"

    results: dict[str, RegimeMetrics] = {}
    for label, group in strat.groupby(regime):
        equity = (1.0 + group).cumprod()
        total = float(equity.iloc[-1] - 1.0) if len(group) else 0.0
        results[str(label)] = RegimeMetrics(
            n_bars=len(group),
            total_return=total,
            sharpe=sharpe_ratio(group),
        )
    return results
