from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class ChandeMomentumStrategy(BaseStrategy):
    """Chande Momentum Oscillator (Tushar Chande), traded as mean reversion.

    Notes:
        CMO = 100 * (sum of up moves - sum of down moves) / (sum of up + sum of down) over a
        trailing `window`, ranging in [-100, 100]. Unlike RSI it uses UNSMOOTHED sums and is
        symmetric, so it swings to the extremes faster. Traded here as mean reversion: long when
        CMO < -`threshold` (heavy recent selling, oversold), short when CMO > +`threshold`
        (overbought), flat between. Up/down moves are trailing diffs -- no look-ahead; a flat
        window (no moves) makes CMO undefined (0/0 -> NaN), which never trips a threshold, so the
        signal stays flat.
    """

    name: ClassVar[str] = "chande_momentum"
    research_citations: ClassVar[list[str]] = [
        "Chande, Tushar S., and Stanley Kroll. The New Technical Trader. Wiley, 1994 "
        "(Chande Momentum Oscillator)."
    ]

    def __init__(self, window: int = 14, threshold: float = 50.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < threshold < 100.0:
            raise ValueError("threshold must be in (0, 100)")
        self.window = window
        self.threshold = threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "threshold": self.threshold}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        change = data["close"].diff()
        up = change.clip(lower=0.0)
        down = (-change).clip(lower=0.0)
        sum_up = up.rolling(self.window).sum()
        sum_down = down.rolling(self.window).sum()
        total = sum_up + sum_down
        with np.errstate(divide="ignore", invalid="ignore"):
            cmo = 100.0 * (sum_up - sum_down) / total.replace(0.0, np.nan)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[cmo < -self.threshold] = 1.0  # oversold -> long
        signals.loc[cmo > self.threshold] = -1.0  # overbought -> short
        return signals
