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
    """Cross-sectional reversal (Lehmann 1990; Jegadeesh 1990): the NEGATED trailing return over
    ``lookback`` bars -- long recent losers, short recent winners. The caller picks the horizon: a
    short ``lookback`` (~5 bars) is weekly reversal, ~21 bars is the 1-month (monthly) reversal of
    Jegadeesh (1990)."""
    return -(prices / prices.shift(lookback) - 1.0)


def low_volatility_signal(prices: pd.DataFrame, vol_window: int) -> pd.DataFrame:
    """Low-volatility anomaly (Baker, Bradley & Wurgler 2011; Ang et al. 2006): rank by INVERSE
    trailing realized volatility -- long low-vol names, short high-vol. The signal is the NEGATED
    rolling standard deviation of trailing simple returns over ``vol_window`` bars, so the calmest
    names score highest. Each return uses only prices <= t, so the signal is causal; the first
    ``vol_window`` rows are NaN (no full return window yet)."""
    returns = prices.pct_change()
    return -returns.rolling(vol_window).std()


def residual_momentum_signal(
    prices: pd.DataFrame, lookback: int, skip: int = 0, mean_window: int = 60
) -> pd.DataFrame:
    """Residual momentum (Blitz, Huij & Martens 2011), cross-sectional analog: momentum of returns
    net of each name's OWN trailing-mean drift. The residual return is the simple return minus its
    trailing mean over ``mean_window``; the signal sums the residual over ``lookback`` bars ending
    ``skip`` bars ago. Long names running above their own trend, short those below -- steadier and
    less crash-prone than raw price momentum. Every term is trailing / shifted -- no look-ahead.
    Documented proxy: this removes own-drift, not a market beta (there is no market series in a
    self-contained panel)."""
    returns = prices.pct_change()
    residual = returns - returns.rolling(mean_window).mean()
    return residual.rolling(lookback).sum().shift(skip)


def risk_adjusted_momentum_signal(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Volatility-scaled (risk-adjusted) momentum: rank by the trailing mean return DIVIDED by the
    trailing return volatility over ``lookback`` bars -- a Sharpe-like trend score (cf. the vol
    scaling of Moskowitz, Ooi & Pedersen 2012). Distinct from raw cumulative-return momentum: two
    names with the same total return but different volatility rank differently, favouring the
    steadier trend. Trailing rolling mean/std of returns -- no look-ahead; the first ``lookback``
    rows are NaN. A zero-volatility window yields NaN and is excluded by the ranker that day."""
    returns = prices.pct_change()
    mean = returns.rolling(lookback).mean()
    std = returns.rolling(lookback).std()
    return mean / std.replace(0.0, np.nan)


def high_proximity_signal(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """52-week-high factor (George & Hwang 2004), cross-sectional: rank by proximity to the trailing
    ``window``-bar high -- ``price / rolling_max``. Names trading near their running high (ratio -> 1)
    score highest and are bought; names far below theirs are shorted. The rolling max includes the
    current bar, so it uses only prices <= t (causal); the first ``window`` - 1 rows are NaN."""
    return prices / prices.rolling(window).max()


def value_signal(prices: pd.DataFrame, scores: Mapping[str, float]) -> pd.DataFrame:
    """Cross-sectional value (Fama & French 1992; Asness et al. 2013): rank on each symbol's
    UndervaluationScore (ADR-022). The score is a static as-of snapshot broadcast across every
    date (point-in-time value history is deferred, ADR-024). An unscored symbol is NaN -> excluded
    by the ranker that day."""
    row = np.array([scores.get(col, np.nan) for col in prices.columns], dtype=float)
    broadcast = np.repeat(row[None, :], len(prices), axis=0)
    return pd.DataFrame(broadcast, index=prices.index, columns=prices.columns)
