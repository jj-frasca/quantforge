from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class SqueezeBreakoutStrategy(BaseStrategy):
    """John Carter's TTM squeeze: trade the breakout when compressed volatility expands.

    Notes:
        A "squeeze" is on when the Bollinger Bands sit ENTIRELY inside the Keltner Channels
        (bb_upper < kc_upper and bb_lower > kc_lower) -- range-based volatility (ATR) exceeds
        deviation-based volatility (std), the classic coiled-spring compression. Both bands share
        one SMA midline over `window`; BB half-width = bb_num_std * rolling std, KC half-width =
        kc_multiple * ATR. While the squeeze is on we stand aside (flat). When it releases
        (bands expand back out), we take the direction of momentum (close - midline) and carry
        that position until the squeeze re-engages. Momentum sign chooses the breakout direction,
        per Carter (2005). The release/carry logic is path-dependent, so signals are built with a
        forward pass; every input is a trailing rolling stat -- no look-ahead. A flat low-vol band
        keeps the squeeze permanently on and the signal flat.
    """

    name: ClassVar[str] = "squeeze_breakout"
    research_citations: ClassVar[list[str]] = [
        "Carter, John F. Mastering the Trade. McGraw-Hill, 2005."
    ]

    def __init__(self, window: int = 20, bb_num_std: float = 2.0, kc_multiple: float = 1.5) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if bb_num_std <= 0.0:
            raise ValueError("bb_num_std must be > 0")
        if kc_multiple <= 0.0:
            raise ValueError("kc_multiple must be > 0")
        self.window = window
        self.bb_num_std = bb_num_std
        self.kc_multiple = kc_multiple

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "window": self.window,
            "bb_num_std": self.bb_num_std,
            "kc_multiple": self.kc_multiple,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        midline = close.rolling(self.window).mean()
        std = close.rolling(self.window).std()
        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = true_range.rolling(self.window).mean()

        bb_half = self.bb_num_std * std
        kc_half = self.kc_multiple * atr
        squeeze_on = (bb_half < kc_half).to_numpy()
        momentum = (close - midline).to_numpy()

        valid = ~(np.isnan(std.to_numpy()) | np.isnan(atr.to_numpy()) | np.isnan(momentum))

        out = np.zeros(len(momentum))
        position = 0.0
        for i in range(len(momentum)):
            if not valid[i]:
                position = 0.0
                out[i] = 0.0
                continue
            if squeeze_on[i]:
                position = 0.0
            else:
                just_fired = i > 0 and bool(squeeze_on[i - 1])
                if just_fired or position == 0.0:
                    mom = momentum[i]
                    position = 1.0 if mom > 0.0 else (-1.0 if mom < 0.0 else 0.0)
            out[i] = position
        return pd.Series(out, index=data.index)
