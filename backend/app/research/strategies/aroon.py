from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class AroonStrategy(BaseStrategy):
    """Aroon trend: is a new high or a new low more recent? Long when up-trend dominates.

    Notes:
        Over a trailing `window`, Aroon-Up = 100 * (bars since the window's highest high were
        made, inverted) and Aroon-Down the same for the lowest low: Aroon-Up is 100 when the
        most recent bar set the high, 0 when the high is the oldest bar in the window. Long when
        Aroon-Up > Aroon-Down (highs are fresher than lows -> up-trend), short when Aroon-Down >
        Aroon-Up, flat when equal or during warmup. The rolling argmax/argmin use only bars up to
        and including t (each bar's high/low is known at its close) -- no look-ahead.
    """

    name: ClassVar[str] = "aroon"
    research_citations: ClassVar[list[str]] = [
        "Chande, Tushar S. 'Aroon' (1995). Technical Analysis of Stocks & Commodities."
    ]

    def __init__(self, window: int = 25) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self.window = window

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        # Position of the extreme within each trailing window: 0 = oldest bar, window-1 = newest.
        idx_high = data["high"].rolling(self.window).apply(np.argmax, raw=True)
        idx_low = data["low"].rolling(self.window).apply(np.argmin, raw=True)
        aroon_up = 100.0 * idx_high / (self.window - 1)
        aroon_down = 100.0 * idx_low / (self.window - 1)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[aroon_up > aroon_down] = 1.0
        signals.loc[aroon_down > aroon_up] = -1.0
        return signals
