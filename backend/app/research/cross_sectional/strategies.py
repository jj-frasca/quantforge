import warnings
from collections.abc import Mapping

import numpy as np
import pandas as pd


def cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional (per-date) rank of a panel: ``df.rank(axis=1, pct=True)`` — each row is ranked
    across symbols only and expressed as a percentile in (0, 1], highest value -> 1.0. This is the
    ``rank(...)`` operator of the WorldQuant formulaic alphas (Kakushadze 2016), used to combine
    several sub-expressions on a common scale before the engine ranks the result. Per-row, so it is
    trivially causal (a row never references another date); a NaN stays NaN and is excluded."""
    return df.rank(axis=1, pct=True)


def cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row cross-sectional z-score: (x - row mean) / row std. Puts factors on a common scale so
    they combine fairly (the bias-correction / standardization step of ADR-028). Per-row, so it is
    causal (a row never references another date); a degenerate row (zero cross-sectional std) yields
    NaN and is excluded by the ranker that day."""
    mean = df.mean(axis=1)
    std = df.std(axis=1).replace(0.0, np.nan)
    return df.sub(mean, axis=0).div(std, axis=0)


def composite_signal(prices: pd.DataFrame, lookback: int = 126) -> pd.DataFrame:
    """Multi-factor z-score composite (ADR-028): cross-sectionally standardize several established
    factors each date and rank on their MEAN z-score -- the dependency-free precursor to
    learning-to-rank. Combining orthogonal factors (momentum + low-volatility + 52-week-high +
    residual momentum) is more robust than any single sort (raw factors embed biases; standardizing
    then averaging is the honest first step). Each component is trailing/causal, so the composite is
    causal; a name missing one factor is averaged over the factors it does have."""
    components = [
        cs_zscore(momentum_signal(prices, lookback, skip=21)),
        cs_zscore(low_volatility_signal(prices, lookback)),
        cs_zscore(high_proximity_signal(prices, lookback)),
        cs_zscore(residual_momentum_signal(prices, lookback, skip=21, mean_window=60)),
    ]
    stacked = np.stack([c.to_numpy() for c in components])  # (n_factors, n_dates, n_symbols)
    with warnings.catch_warnings():
        # An all-NaN cell (no factor available yet, e.g. warmup) -> NaN, excluded by the ranker.
        warnings.simplefilter("ignore", category=RuntimeWarning)
        composite = np.nanmean(stacked, axis=0)
    return pd.DataFrame(composite, index=prices.index, columns=prices.columns)


def alpha34_signal(
    prices: pd.DataFrame, short_window: int = 2, long_window: int = 5
) -> pd.DataFrame:
    """WorldQuant Alpha#34 (Kakushadze 2016), close-only: combine a declining-volatility signal with
    a mild reversal. The rank-inverse of the short/long realized-vol ratio favors names whose
    volatility is falling; the rank-inverse of the 1-bar price change favors recent underperformers.
    Sum the two (the paper's outer rank is dropped since the engine ranks the result). Trailing std +
    shift -- no look-ahead."""
    returns = prices.pct_change()
    std_short = returns.rolling(short_window).std()
    std_long = returns.rolling(long_window).std().replace(0.0, np.nan)
    vol_ratio = std_short / std_long
    delta_close = prices - prices.shift(1)
    return (1.0 - cs_rank(vol_ratio)) + (1.0 - cs_rank(delta_close))


def alpha19_signal(
    prices: pd.DataFrame, change_lag: int = 7, sum_window: int = 250
) -> pd.DataFrame:
    """WorldQuant Alpha#19 (Kakushadze 2016), close-only: -sign(close - close.shift(change_lag))
    scaled by (1 + cross-sectional rank of (1 + trailing-sum of returns over sum_window)). Fades the
    recent `change_lag`-bar move, weighted up for names with strong long-horizon cumulative return.
    Trailing sum + shift -- no look-ahead; the first sum_window rows are NaN."""
    returns = prices.pct_change()
    change = prices - prices.shift(change_lag)
    long_sum = returns.rolling(sum_window).sum()
    return -np.sign(change) * (1.0 + cs_rank(1.0 + long_sum))


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


def _broadcast_scores(prices: pd.DataFrame, scores: Mapping[str, float]) -> pd.DataFrame:
    """Broadcast a static per-symbol score across every date. Unscored symbols become NaN, which
    the cross-sectional ranker excludes that day."""
    row = np.array([scores.get(col, np.nan) for col in prices.columns], dtype=float)
    broadcast = np.repeat(row[None, :], len(prices), axis=0)
    return pd.DataFrame(broadcast, index=prices.index, columns=prices.columns)


def value_signal(prices: pd.DataFrame, scores: Mapping[str, float]) -> pd.DataFrame:
    """Cross-sectional value (Fama & French 1992; Asness et al. 2013): rank on each symbol's
    UndervaluationScore (ADR-022). The score is a static as-of snapshot broadcast across every
    date (point-in-time value history is deferred, ADR-024). An unscored symbol is NaN -> excluded
    by the ranker that day."""
    return _broadcast_scores(prices, scores)


def quality_signal(prices: pd.DataFrame, scores: Mapping[str, float]) -> pd.DataFrame:
    """Cross-sectional quality (Piotroski 2000; Novy-Marx 2013; ADR-029): rank on each symbol's
    fundamental quality_score. Like value, a static as-of snapshot broadcast across every date
    (point-in-time fundamentals history deferred, ADR-029); an unscored symbol is NaN -> excluded
    that day. Judged by the SAME DSR/PBO/holdout gate as every technical factor — fundamentals
    earn their place, they are not assumed."""
    return _broadcast_scores(prices, scores)
