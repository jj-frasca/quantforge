import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.cross_sectional.engine import asset_returns

_MIN_RANKED_NAMES = 2
_MIN_PERIODS_FOR_SUMMARY = 2
# Guards the IR when every date scored the identical IC (dispersion is exactly zero, which is an
# artifact of a degenerate series rather than infinite information).
_MIN_STD = 1e-12


class ICSummary(BaseModel):
    """Summary statistics of a rank-IC series (ADR-035). `t_stat` assumes independent periods and
    is therefore OPTIMISTIC for a slow signal whose IC series is autocorrelated — it is a screening
    diagnostic, not an inferential claim."""

    model_config = ConfigDict(frozen=True)

    mean: float
    std: float
    information_ratio: float
    t_stat: float
    hit_rate: float
    n_periods: int


def rank_ic(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Per-date Spearman rank correlation between the signal cross-section at t and each asset's
    return from t to t+1 (ADR-035).

    Causality matches `portfolio_returns` exactly: rank on t, realize t+1. Dates that cannot yield
    a defined correlation — fewer than two ranked names, or a constant signal or return
    cross-section — are DROPPED rather than recorded as zero, because "not measurable" is not the
    same observation as "no information" and scoring it zero would bias the mean toward the null.
    """
    if list(signals.columns) != list(prices.columns):
        raise ValueError("signals and prices must share the same symbol columns, in order")

    forward = asset_returns(prices).shift(-1)
    # Rank only names scorable on BOTH sides that date, so an unscorable name is excluded rather
    # than ranked against a hole. Vectorized row-wise: a per-date Python loop is ~500x slower on a
    # full-universe panel, and this runs inside every cross-sectional search.
    scorable = signals.notna() & forward.notna()
    s_rank = signals.where(scorable).rank(axis=1)
    r_rank = forward.where(scorable).rank(axis=1)
    s_dev = s_rank.sub(s_rank.mean(axis=1), axis=0)
    r_dev = r_rank.sub(r_rank.mean(axis=1), axis=0)
    s_norm = np.sqrt((s_dev**2).sum(axis=1))
    r_norm = np.sqrt((r_dev**2).sum(axis=1))
    ic = (s_dev * r_dev).sum(axis=1) / (s_norm * r_norm)
    # Drop, never zero-fill: too few names to rank, or a flat cross-section on either side (zero
    # dispersion -> the correlation is undefined, not zero).
    defined = (scorable.sum(axis=1) >= _MIN_RANKED_NAMES) & (s_norm > 0.0) & (r_norm > 0.0)
    return ic[defined].rename("rank_ic")


def summarize_ic(series: pd.Series) -> ICSummary | None:
    """Summarize a rank-IC series. Returns None below two periods: a single date carries no
    dispersion estimate, so there is no IR and no t-statistic to report honestly."""
    n = len(series)
    if n < _MIN_PERIODS_FOR_SUMMARY:
        return None
    values = series.to_numpy(dtype=float)
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    ir = mean / max(std, _MIN_STD)
    return ICSummary(
        mean=mean,
        std=std,
        information_ratio=ir,
        t_stat=ir * float(np.sqrt(n)),
        hit_rate=float(np.mean(values > 0.0)),
        n_periods=n,
    )
