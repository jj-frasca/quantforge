from collections.abc import Mapping

import numpy as np
import pandas as pd


def momentum_signal(prices: pd.DataFrame, lookback: int, skip: int = 0) -> pd.DataFrame:
    """Cross-sectional momentum (Jegadeesh & Titman 1993): trailing return over ``lookback`` bars
    ending ``skip`` bars ago. ``skip`` (typically ~1 month) sidesteps the short-term reversal that
    would otherwise contaminate the momentum signal. Built with ``.shift`` so row t uses only
    prices <= t; the first ``lookback + skip`` rows are NaN (no window yet)."""
    return prices.shift(skip) / prices.shift(skip + lookback) - 1.0


def reversal_signal(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Short-term reversal (Lehmann 1990; Jegadeesh 1990): the NEGATED trailing return over a short
    ``lookback`` (~5 bars) — long recent losers, short recent winners."""
    return -(prices / prices.shift(lookback) - 1.0)


def value_signal(prices: pd.DataFrame, scores: Mapping[str, float]) -> pd.DataFrame:
    """Cross-sectional value (Fama & French 1992; Asness et al. 2013): rank on each symbol's
    UndervaluationScore (ADR-022). The score is a static as-of snapshot broadcast across every
    date (point-in-time value history is deferred, ADR-024). An unscored symbol is NaN -> excluded
    by the ranker that day."""
    row = np.array([scores.get(col, np.nan) for col in prices.columns], dtype=float)
    broadcast = np.repeat(row[None, :], len(prices), axis=0)
    return pd.DataFrame(broadcast, index=prices.index, columns=prices.columns)
