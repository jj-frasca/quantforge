from numbers import Integral
from typing import Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.research.cross_sectional.engine import _is_finite_native_scalar, asset_returns

_MIN_RANKED_NAMES = 2
_MIN_PERIODS_FOR_SUMMARY = 2
# Guards the IR when every date scored the identical IC (dispersion is exactly zero, which is an
# artifact of a degenerate series rather than infinite information).
_MIN_STD = 1e-12


class ICSummary(BaseModel):
    """Summary statistics of a rank-IC series (ADR-035). `t_stat` assumes independent periods and
    is therefore OPTIMISTIC for a slow signal whose IC series is autocorrelated — it is a screening
    diagnostic, not an inferential claim."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    # Finite-only mean preserves coherent historical endpoint roundoff (ADR-267).
    mean: float = Field(allow_inf_nan=False)
    std: float = Field(ge=0, allow_inf_nan=False)
    information_ratio: float = Field(allow_inf_nan=False)
    t_stat: float = Field(allow_inf_nan=False)
    hit_rate: float = Field(ge=0, le=1, allow_inf_nan=False)
    n_periods: int = Field(ge=_MIN_PERIODS_FOR_SUMMARY)

    @field_validator("n_periods", mode="before")
    @classmethod
    def _validate_period_count(cls, value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise ValueError("n_periods must be a native integer count")
        return int(value)

    @model_validator(mode="after")
    def _validate_statistic_identity(self) -> Self:
        try:
            expected_ir = self.mean / max(self.std, _MIN_STD)
            expected_t = self.information_ratio * float(np.sqrt(self.n_periods))
        except (TypeError, OverflowError, FloatingPointError) as exc:
            raise ValueError("IC summary statistics must be measurable") from exc
        if self.information_ratio != expected_ir or self.t_stat != expected_t:
            raise ValueError("IC summary IR and t_stat must match the original formulas")
        return self


def _native_average_ranks(frame: pd.DataFrame, scorable: pd.DataFrame) -> pd.DataFrame:
    """Preserve native scalar order before pairwise masking adds missing values (ADR-264)."""
    rank_input = frame
    if any(
        isinstance(dtype, np.dtype)
        and (
            dtype.kind in {"i", "u"}
            or (dtype.kind == "f" and dtype.itemsize > np.dtype(float).itemsize)
        )
        for dtype in frame.dtypes
    ):
        rank_input = frame.astype(object)
    return rank_input.where(scorable).rank(axis=1)


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
    if signals.isin([np.inf, -np.inf]).any().any():
        raise ValueError("cross-sectional signals must not contain infinite scores")
    # Rank only names scorable on BOTH sides that date, so an unscorable name is excluded rather
    # than ranked against a hole. Vectorized row-wise: a per-date Python loop is ~500x slower on a
    # full-universe panel, and this runs inside every cross-sectional search.
    scorable = signals.notna() & forward.notna()
    s_rank = _native_average_ranks(signals, scorable)
    r_rank = _native_average_ranks(forward, scorable)
    s_dev = s_rank.sub(s_rank.mean(axis=1), axis=0)
    r_dev = r_rank.sub(r_rank.mean(axis=1), axis=0)
    s_norm = np.sqrt((s_dev**2).sum(axis=1))
    r_norm = np.sqrt((r_dev**2).sum(axis=1))
    ic = (s_dev * r_dev).sum(axis=1) / (s_norm * r_norm)
    # Drop, never zero-fill: too few names to rank, or a flat cross-section on either side (zero
    # dispersion -> the correlation is undefined, not zero).
    defined = (scorable.sum(axis=1) >= _MIN_RANKED_NAMES) & (s_norm > 0.0) & (r_norm > 0.0)
    measured = ic[defined]
    if not np.isfinite(measured).all():
        raise ValueError("rank IC must be finite")
    return measured.clip(-1.0, 1.0).rename("rank_ic")


def summarize_ic(series: pd.Series) -> ICSummary | None:
    """Summarize a rank-IC series. Returns None below two periods: a single date carries no
    dispersion estimate, so there is no IR and no t-statistic to report honestly."""
    for value in series:
        try:
            invalid = (
                np.iscomplexobj(value)
                or not _is_finite_native_scalar(value)
                or value < -1
                or value > 1
            )
        except TypeError as exc:
            raise ValueError("IC observations must be finite real values in [-1, 1]") from exc
        if invalid:
            raise ValueError("IC observations must be finite real values in [-1, 1]")
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
