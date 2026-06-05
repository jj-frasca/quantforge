from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class TrendFilteredMeanReversionStrategy(BaseStrategy):
    """Mean reversion within a longer-term trend: long oversold *in an uptrend*, short
    overbought *in a downtrend*, flat otherwise.

    Notes:
        First multi-indicator strategy in the catalog. The semantic move is
        *combination*: a short-term mean-reversion signal (z-score of close) is GATED
        by a longer-term trend signal (close vs. trend SMA). The reasoning: blind
        mean reversion bets get cut by sustained moves — buying a falling knife is
        the classic retail mistake. Filtering by the longer trend means we only buy
        oversold dips inside an uptrend (where mean reversion is more reliable) and
        short rallies inside a downtrend.

        Implementation choices (the "why this code looks like this"):

        - Two windows: `z_window` for the z-score (short-term: typical 10-30 bars) and
          `trend_window` for the SMA (long-term: typical 100-200 bars). Cross-param
          rule: `trend_window > z_window`. If a user inverts them the strategy degenerates
          (the "trend" runs at the same horizon as the bet), so we reject in __init__.
        - Z-score uses `(close - rolling_mean) / rolling_std` over `z_window`. Trailing
          rolling means and stds → no look-ahead.
        - Trend SMA is a plain rolling mean of close over `trend_window`. Trailing → no
          look-ahead. We compare `close > trend` rather than `close > shifted_trend`
          because a same-bar comparison against a TRAILING average is causal.
        - During warmup (before either window fills) the rolling stats are NaN; we
          fillna(False) on the boolean masks so the strategy stays flat — never
          accidentally long because a NaN > something evaluates oddly.
        - Discrete +/-1 / 0 signal — keeps the §8 invariant clean. A future weighted
          variant (e.g. scale by |z|) would be a separate strategy class.

        Connors & Alvarez (2009) popularized this combination in retail quant — they
        run RSI(2) inside a 200-day SMA filter, which is the same shape with different
        indicators. Our version uses z-score for the short signal because it composes
        naturally with the existing `MeanReversionStrategy` (same z math).
    """

    name: ClassVar[str] = "trend_filtered_mean_reversion"
    research_citations: ClassVar[list[str]] = [
        "Connors, Larry & Alvarez, Cesar. Short Term Trading Strategies That Work. "
        "TradingMarkets Publishing Group, 2009."
    ]

    def __init__(
        self,
        z_window: int = 20,
        z_threshold: float = 1.5,
        trend_window: int = 100,
    ) -> None:
        if z_window < 2:
            raise ValueError("z_window must be >= 2")
        if z_threshold <= 0:
            raise ValueError("z_threshold must be > 0")
        if trend_window < 2:
            raise ValueError("trend_window must be >= 2")
        if trend_window <= z_window:
            raise ValueError("trend_window must be > z_window (the trend is the longer view)")
        self.z_window = z_window
        self.z_threshold = z_threshold
        self.trend_window = trend_window

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "z_window": self.z_window,
            "z_threshold": self.z_threshold,
            "trend_window": self.trend_window,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]

        mean = close.rolling(self.z_window).mean()
        std = close.rolling(self.z_window).std()
        z = (close - mean) / std.where(std > 0)

        trend = close.rolling(self.trend_window).mean()

        # Boolean masks for each leg; fillna(False) so the warmup region stays flat.
        is_uptrend = (close > trend).fillna(False)
        is_downtrend = (close < trend).fillna(False)
        oversold = (z < -self.z_threshold).fillna(False)
        overbought = (z > self.z_threshold).fillna(False)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[oversold & is_uptrend] = 1.0
        signals.loc[overbought & is_downtrend] = -1.0
        return signals
