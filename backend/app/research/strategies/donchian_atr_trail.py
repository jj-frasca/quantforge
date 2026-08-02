from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class DonchianATRTrailStrategy(BaseStrategy):
    """Turtle-style channel breakout entry with a Chandelier (ATR trailing-stop) exit.

    Notes:
        Entry is the classic Donchian rule -- go long when the close breaks above the prior
        `entry_window`-bar high, short when it breaks below the prior low. The exit is NOT the
        opposite channel but Chuck LeBeau's Chandelier stop: while long, exit when the close
        falls below highest_high(atr_window) - atr_multiple * ATR; while short, exit when the
        close rises above lowest_low(atr_window) + atr_multiple * ATR. The trailing stop lets a
        winner run while capping give-back, which is the Turtle system's edge over a symmetric
        channel exit. State is path-dependent (the stop ratchets with the position), so signals
        are built with an explicit forward pass -- but every input (prior-window extremes via
        shift, current-bar ATR) is trailing, so there is no look-ahead. A flat (zero-range)
        series never breaks a channel and stays flat.
    """

    name: ClassVar[str] = "donchian_atr_trail"
    research_citations: ClassVar[list[str]] = [
        "Faith, Curtis M. Way of the Turtle. McGraw-Hill, 2007.",
        "LeBeau, Charles, and David W. Lucas. Technical Traders Guide to Computer Analysis "
        "of the Futures Markets. Business One Irwin, 1992.",
    ]

    def __init__(
        self, entry_window: int = 20, atr_window: int = 22, atr_multiple: float = 3.0
    ) -> None:
        if entry_window < 2:
            raise ValueError("entry_window must be >= 2")
        if atr_window < 2:
            raise ValueError("atr_window must be >= 2")
        if atr_multiple <= 0.0:
            raise ValueError("atr_multiple must be > 0")
        self.entry_window = entry_window
        self.atr_window = atr_window
        self.atr_multiple = atr_multiple

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "entry_window": self.entry_window,
            "atr_window": self.atr_window,
            "atr_multiple": self.atr_multiple,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = true_range.rolling(self.atr_window).mean()

        entry_high = close.shift(1).rolling(self.entry_window).max()
        entry_low = close.shift(1).rolling(self.entry_window).min()
        chandelier_long = high.rolling(self.atr_window).max() - self.atr_multiple * atr
        chandelier_short = low.rolling(self.atr_window).min() + self.atr_multiple * atr

        close_v = close.to_numpy()
        eh = entry_high.to_numpy()
        el = entry_low.to_numpy()
        long_stop = chandelier_long.to_numpy()
        short_stop = chandelier_short.to_numpy()

        out = np.zeros(len(close_v))
        position = 0.0
        for i in range(len(close_v)):
            if np.isnan(eh[i]) or np.isnan(long_stop[i]) or np.isnan(short_stop[i]):
                position = 0.0
                out[i] = 0.0
                continue
            price = close_v[i]
            stopped_out = (position > 0.0 and price < long_stop[i]) or (
                position < 0.0 and price > short_stop[i]
            )
            if stopped_out:
                position = 0.0
            if position == 0.0:
                if price > eh[i]:
                    position = 1.0
                elif price < el[i]:
                    position = -1.0
            out[i] = position
        return pd.Series(out, index=data.index)
