from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy

_SHORT, _MEDIUM, _LONG = 7, 14, 28
_W_SHORT, _W_MEDIUM, _W_LONG = 4.0, 2.0, 1.0


class UltimateOscillatorStrategy(BaseStrategy):
    """Larry Williams' Ultimate Oscillator, traded as mean reversion.

    Notes:
        Buying pressure BP = close - min(low, prev_close); true range TR = max(high, prev_close) -
        min(low, prev_close). Averages of BP/TR over three classic windows (7, 14, 28) are combined
        with weights 4:2:1 into UO = 100 * (4*avg7 + 2*avg14 + avg28) / 7, bounded in [0, 100].
        Long when UO < `oversold` (spent selling), short when UO > `overbought`, flat between. The
        multi-timeframe blend is designed to cut the false divergences a single-window oscillator
        throws. All rolling sums are trailing and prev_close is a shift -- no look-ahead; a flat
        window (zero true range) leaves UO undefined and the signal stays flat.
    """

    name: ClassVar[str] = "ultimate_oscillator"
    research_citations: ClassVar[list[str]] = [
        "Williams, Larry. 'The Ultimate Oscillator'. Technical Analysis of Stocks & "
        "Commodities (1976)."
    ]

    def __init__(self, oversold: float = 30.0, overbought: float = 70.0) -> None:
        if not 0.0 < oversold < overbought < 100.0:
            raise ValueError("require 0 < oversold < overbought < 100")
        self.oversold = oversold
        self.overbought = overbought

    @property
    def parameters(self) -> dict[str, object]:
        return {"oversold": self.oversold, "overbought": self.overbought}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
        buying_pressure = close - true_low
        true_range = pd.concat([high, prev_close], axis=1).max(axis=1) - true_low

        def average(window: int) -> pd.Series:
            return buying_pressure.rolling(window).sum() / true_range.rolling(window).sum()

        uo = (
            100.0
            * (_W_SHORT * average(_SHORT) + _W_MEDIUM * average(_MEDIUM) + _W_LONG * average(_LONG))
            / (_W_SHORT + _W_MEDIUM + _W_LONG)
        )

        signals = pd.Series(0.0, index=data.index)
        signals.loc[uo < self.oversold] = 1.0
        signals.loc[uo > self.overbought] = -1.0
        return signals
