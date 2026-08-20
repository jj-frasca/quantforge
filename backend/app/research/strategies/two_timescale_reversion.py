from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class TwoTimescaleReversionStrategy(BaseStrategy):
    """Trade the fast residual around a slowly-drifting level (ADR-056).

    Notes:
        `level` is an exponentially weighted mean over `level_span` — the steady-state form of the
        filter for a random-walk level observed with transient noise. The residual is z-scored
        against its OWN standard deviation over the separate, shorter `scale_window`.

        The two timescales are the point. Every other reverting strategy in the catalog
        (`mean_reversion`, Bollinger, Keltner, VWAP reversion, the oscillators) uses one window for
        both jobs, and one window cannot do both: short enough to track the level absorbs the
        deviation into it, long enough to isolate the deviation lags the level. ADR-055 measured
        that structure converting 29-45% of a fast band-reversion edge.

        Trailing statistics only (`ewm` and `rolling` are both causal), so no look-ahead.
        Avellaneda & Lee (2010)'s residual decomposition, applied to a single name.
    """

    name: ClassVar[str] = "two_timescale_reversion"
    research_citations: ClassVar[list[str]] = [
        "Avellaneda, M. & Lee, J.-H. 'Statistical Arbitrage in the U.S. Equities Market'. "
        "Quantitative Finance 10, no. 7 (2010), pp. 761-782."
    ]

    def __init__(self, level_span: int = 60, scale_window: int = 10, k: float = 2.0) -> None:
        if level_span < 2:
            raise ValueError("level_span must be >= 2")
        if scale_window < 2:
            raise ValueError("scale_window must be >= 2")
        if k <= 0:
            raise ValueError("k must be > 0")
        self.level_span = level_span
        self.scale_window = scale_window
        self.k = k

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "level_span": self.level_span,
            "scale_window": self.scale_window,
            "k": self.k,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        level = close.ewm(span=self.level_span, adjust=False).mean()
        residual = close - level
        scale = residual.rolling(self.scale_window).std()
        z_score = (residual / scale.where(scale > 0.0)).fillna(0.0)
        return (-(z_score / self.k)).clip(-1.0, 1.0)
