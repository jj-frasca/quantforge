from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class MACDCrossoverStrategy(BaseStrategy):
    """MACD crossover: long when MACD line is above its signal line, short when below.

    Notes:
        MACD = EMA(close, fast) - EMA(close, slow); signal_line = EMA(MACD, signal).
        Position is +1 when MACD > signal (trend-up confirmation), -1 when MACD < signal,
        and 0 exactly at the crossover bar (a vanishing measure). This is the
        sign-of-the-histogram rule.

        Implementation choices (the "why this code looks like this"):

        - We use pandas `ewm(span=N, adjust=False)` — the "recursive" EMA convention used
          by the technical-analysis literature. `adjust=True` would use an equal-weighted
          formula until the window fills, which is *not* the conventional MACD definition
          and would silently shift the signal in the warmup region.
        - EMA is causal by construction: EMA_t depends only on EMA_{t-1} and close_t —
          no look-ahead.
        - We don't subtract the signal line at the engine level; we expose only the
          discrete `sign(MACD - signal)` because that's the trading rule. A future
          "use the histogram value as a weighted signal" variant would be a separate
          strategy class.
        - Conventional defaults: 12/26/9 (Appel's original numbers).
    """

    name: ClassVar[str] = "macd_crossover"
    research_citations: ClassVar[list[str]] = [
        "Appel, Gerald. Technical Analysis: Power Tools for Active Investors. FT Press, 2005."
    ]

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        if fast < 1:
            raise ValueError("fast EMA span must be >= 1")
        if signal < 1:
            raise ValueError("signal EMA span must be >= 1")
        if fast >= slow:
            raise ValueError("fast EMA span must be < slow EMA span")
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def parameters(self) -> dict[str, object]:
        return {"fast": self.fast, "slow": self.slow, "signal": self.signal}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        # adjust=False is the conventional MACD recursion (see docstring Notes).
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()

        histogram = macd_line - signal_line
        signals = pd.Series(0.0, index=data.index)
        signals.loc[histogram > 0] = 1.0
        signals.loc[histogram < 0] = -1.0
        return signals
