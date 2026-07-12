import pandas as pd

from app.research.cross_sectional.panel import long_short_weights


def asset_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol simple returns; the first bar is 0 (no prior price), matching the single-name
    engine's `prices.pct_change().fillna(0.0)`."""
    return prices.pct_change().fillna(0.0)


def portfolio_returns(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    quantile: float = 0.2,
    cost_rate: float = 0.001,
) -> pd.Series:
    """Realize a cross-sectional portfolio return series from a signal panel (ADR-024).

    Rank each date's signals into dollar-neutral weights, then hold them to earn the NEXT bar's
    return: ``weights.shift(1) * asset_returns`` — identical to the single-name engine's
    ``position.shift(1)``. Turnover ``|Δweights|`` is charged at ``cost_rate``. Because every step
    (pct_change, shift, diff) is causal, ``portfolio_return[t]`` depends only on prices <= t —
    rank on t, trade t+1, no look-ahead.
    """
    if cost_rate < 0:
        raise ValueError("cost_rate must be >= 0")
    weights = (
        long_short_weights(signals, quantile)
        .reindex(index=prices.index, columns=prices.columns)
        .fillna(0.0)
    )
    rets = asset_returns(prices)
    gross = (weights.shift(1).fillna(0.0) * rets).sum(axis=1)
    turnover = weights.diff().abs().fillna(weights.abs()).sum(axis=1)
    net = gross - turnover * cost_rate
    return net


def split_panel_holdout(
    prices: pd.DataFrame,
    holdout_fraction: float = 0.2,
    min_holdout_bars: int = 252,
    min_search_bars: int = 252,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a date-ordered price panel into an in-sample head and a sealed holdout tail — the
    panel analog of `holdout.split_holdout` (same fractions/floors). The holdout is always the
    calendar-latest ``max(holdout_fraction·N, min_holdout_bars)`` rows. Raises if the remaining
    search head would be shorter than ``min_search_bars``."""
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be in (0, 1)")
    n = len(prices)
    holdout_n = max(int(holdout_fraction * n), min_holdout_bars)
    search_n = n - holdout_n
    if search_n < min_search_bars:
        raise ValueError(
            f"insufficient data: {search_n} search bars after a {holdout_n}-bar holdout "
            f"(need >= {min_search_bars})"
        )
    return prices.iloc[:search_n], prices.iloc[search_n:]
