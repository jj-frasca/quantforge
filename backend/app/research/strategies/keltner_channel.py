from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class KeltnerChannelStrategy(BaseStrategy):
    """Keltner Channel breakout: long when close breaks above the upper band, short below.

    Notes:
        First strategy to use OHLC, not just close — `high`/`low` feed the Average True
        Range (ATR), which sets the channel width. The midline is an EMA of close. The
        bands sit at `midline +/- multiplier * ATR`. Because ATR adapts to recent volatility,
        the channel widens in choppy regimes and narrows in calm ones — fewer false
        breakouts in chop than a fixed-window Donchian channel.

        Implementation choices (the "why this code looks like this"):

        - True Range (Wilder 1978) = max of three quantities:
            * today's high - today's low (the intra-day range);
            * |today's high - yesterday's close| (gap-up component);
            * |today's low - yesterday's close| (gap-down component).
          We compute the third only after `close.shift(1)` so day-0 has a NaN previous
          close; True Range falls back to the first quantity then via `pd.concat(...).max(axis=1)`
          which ignores NaN.
        - ATR uses a simple rolling mean of TR over `atr_window`. Wilder's original RMA
          (an EMA with alpha=1/N) is the more traditional choice but is equivalent up to
          smoothing kernel; the SMA variant is easier to reason about and matches what
          most charting libraries call "ATR" today.
        - Midline is `ewm(span, adjust=False)` of close — same recursion convention as
          MACD (see [[research-papers]] entry for Appel 2005).
        - Signal: long on close > upper, short on close < lower, flat between. No
          carry-forward — unlike Donchian, exiting a Keltner band is a normal occurrence
          and we don't want to keep the position when neither band is breached.
        - No look-ahead anywhere: TR uses only past closes via shift(1); rolling means
          are trailing.

        Keltner published the SMA + ATR version in 1960; modern variants (e.g., the
        Linda Bradford Raschke variant) use EMA + ATR which is what we do here.
    """

    name: ClassVar[str] = "keltner_channel"
    research_citations: ClassVar[list[str]] = [
        "Keltner, Chester W. How To Make Money in Commodities. Keltner Statistical Service, 1960.",
        "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978.",
    ]

    def __init__(
        self,
        ma_window: int = 20,
        atr_window: int = 14,
        multiplier: float = 2.0,
    ) -> None:
        if ma_window < 1:
            raise ValueError("ma_window must be >= 1")
        if atr_window < 2:
            raise ValueError("atr_window must be >= 2")
        if multiplier <= 0:
            raise ValueError("multiplier must be > 0")
        self.ma_window = ma_window
        self.atr_window = atr_window
        self.multiplier = multiplier

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "ma_window": self.ma_window,
            "atr_window": self.atr_window,
            "multiplier": self.multiplier,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        # True Range per Wilder (1978): see docstring Notes for the three components.
        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        atr = true_range.rolling(self.atr_window).mean()

        midline = close.ewm(span=self.ma_window, adjust=False).mean()
        upper = midline + self.multiplier * atr
        lower = midline - self.multiplier * atr

        signals = pd.Series(0.0, index=data.index)
        signals.loc[close > upper] = 1.0
        signals.loc[close < lower] = -1.0
        return signals
