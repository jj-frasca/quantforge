import math
from collections.abc import Sequence
from numbers import Integral

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.research.backtesting.metrics import TRADING_DAYS
from app.research.strategies.base import BaseStrategy
from app.validation.result_graph import FrozenResultList

IntArray = npt.NDArray[np.intp]
FloatArray = npt.NDArray[np.float64]


def purged_kfold_splits(
    n_obs: int, n_splits: int, embargo: int = 0
) -> list[tuple[IntArray, IntArray]]:
    """Purged K-Fold CV splits with an embargo (López de Prado 2018, ch. 7).

    Notes:
        Each contiguous fold is the test set; training indices within ``embargo`` of the test
        block are purged, so no training index lies within embargo of any test index (no
        leakage). Every index is tested exactly once.
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    if embargo < 0:
        raise ValueError("embargo must be >= 0")
    if n_obs < n_splits:
        raise ValueError("n_obs must be >= n_splits")

    remainder = n_obs % n_splits
    sizes = [n_obs // n_splits + (1 if i < remainder else 0) for i in range(n_splits)]
    all_idx = np.arange(n_obs, dtype=np.intp)

    splits: list[tuple[IntArray, IntArray]] = []
    start = 0
    for size in sizes:
        end = start + size
        test_idx = np.arange(start, end, dtype=np.intp)
        lo = max(0, start - embargo)
        hi = min(n_obs, end + embargo)
        purged = (all_idx >= lo) & (all_idx < hi)
        train_idx = all_idx[~purged]
        splits.append((train_idx, test_idx))
        start = end
    return splits


class PurgedCVFoldResult(BaseModel):
    """One purged fold: the config chosen on the purged train rows, and its score on the fold."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    selected_config: int = Field(ge=0)
    oos_sharpe: float = Field(allow_inf_nan=False)
    n_train: int = Field(ge=1)
    n_test: int = Field(ge=1)


class PurgedCVResult(BaseModel):
    """Leakage-controlled out-of-sample dispersion of an edge across folds (ADR-039).

    Notes:
        NOT a live-simulation estimate: a fold's training rows include indices AFTER its test
        block, so selection sees the future. That is what the technique buys — many resampled
        paths with boundary leakage purged. ADR-038's walk-forward is the causal counterpart;
        a large gap between the two is itself diagnostic. Sharpes are annualized, matching
        metrics.sharpe_ratio. Diagnostic only — nothing gates on it.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    n_folds: int = Field(ge=1)
    embargo: int = Field(ge=0)
    folds: list[PurgedCVFoldResult]
    mean_oos_sharpe: float = Field(allow_inf_nan=False)
    oos_sharpe_std: float = Field(ge=0.0, allow_inf_nan=False)
    consistency: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    # ADR-078: buy-and-hold scored across the SAME folds, averaged over the folds that were KEPT.
    # `mean_oos_sharpe` is denominated in the drift of the series it was computed on exactly as the
    # walk-forward statistic is (ADR-068), so the two are only interpretable together. Purged CV
    # tests every index once, so this control covers the whole searched window rather than a
    # suffix of it. None means no benchmark was supplied, which is not a benchmark of zero
    # (ADR-067).
    mean_oos_hold_sharpe: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _bind_summary_to_folds(self) -> "PurgedCVResult":
        if len(self.folds) != self.n_folds:
            raise ValueError("n_folds must equal len(folds)")
        scores = [fold.oos_sharpe for fold in self.folds]
        mean = sum(scores) / self.n_folds
        std = (
            math.sqrt(sum((score - mean) ** 2 for score in scores) / (self.n_folds - 1))
            if self.n_folds > 1
            else 0.0
        )
        consistency = sum(score > 0.0 for score in scores) / self.n_folds
        for name, actual, expected in (
            ("mean_oos_sharpe", self.mean_oos_sharpe, mean),
            ("oos_sharpe_std", self.oos_sharpe_std, std),
            ("consistency", self.consistency, consistency),
        ):
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{name} must agree with folds")
        object.__setattr__(self, "folds", FrozenResultList(list(self.folds)))
        return self


def lookback_embargo(configs: Sequence[BaseStrategy], floor: int) -> int:
    """Embargo sized from the longest lookback in the config grid, floored at `floor` (ADR-039).

    Notes:
        The largest integer parameter is a PROXY for the longest window, not a guarantee of one.
        It is correct for every catalog strategy today (`slow`/`window`/`period`/`lookback` are the
        large integers; thresholds and std multipliers are small floats). A fixed constant is wrong
        for two thirds of the catalog, which is the alternative it replaces.
    """
    if floor < 0:
        raise ValueError("floor must be >= 0")
    lookbacks = [
        value
        for config in configs
        for value in config.parameters.values()
        if isinstance(value, int) and not isinstance(value, bool)
    ]
    return max([floor, *lookbacks])


def _sharpe(returns: FloatArray) -> float:
    """Annualized, matching metrics.sharpe_ratio (ADR-039) so folds are comparable with the
    observed, holdout and walk-forward Sharpes."""
    if len(returns) < 2:
        return 0.0
    std = float(returns.std(ddof=1))
    return float(np.sqrt(TRADING_DAYS) * returns.mean() / std) if std > 0 else 0.0


def purged_cv_evaluate(
    performance: FloatArray,
    splits: list[tuple[IntArray, IntArray]],
    *,
    embargo: int,
    benchmark: FloatArray | None = None,
) -> PurgedCVResult:
    """Select on each fold's purged train rows, score that choice on the fold (ADR-039).

    Args:
        performance: (T observations, N configurations) per-bar returns — the matrix PBO consumes.
        splits: purged K-fold splits from ``purged_kfold_splits``.
        embargo: the embargo those splits were built with, recorded on the result so a stored
            measurement says how hard it was actually purged.
        benchmark: optional per-bar buy-and-hold returns for the same window, scored across the
            same folds (ADR-078). Pairing it here rather than at the call site is the point: a
            benchmark measured over a different window is the confound it exists to remove.

    Notes:
        A fold whose training set was purged away entirely has nothing to select on and is
        DROPPED, not scored — counting it would report a selection that never happened. Every
        fold being unusable is an error, not an empty result.
    """
    performance_source = performance
    benchmark_source = benchmark
    performance = np.asarray(performance)
    if performance.ndim != 2 or performance.shape[1] < 2:
        raise ValueError("need >= 2 configurations to select within a fold")
    if not splits:
        raise ValueError("need >= 1 fold")

    n_obs = performance.shape[0]
    if benchmark is not None:
        benchmark = np.asarray(benchmark)
        if benchmark.shape != (n_obs,):
            raise ValueError("benchmark must carry one return per bar of the performance matrix")
    if performance.dtype.kind not in "iuf":
        raise ValueError("performance must carry real numeric returns")
    if benchmark is not None and benchmark.dtype.kind not in "iuf":
        raise ValueError("benchmark must carry real numeric returns")
    with np.errstate(over="ignore", invalid="ignore"):
        performance = np.asarray(performance, dtype=np.float64)
        if benchmark is not None:
            benchmark = np.asarray(benchmark, dtype=np.float64)
    if not np.isfinite(performance).all() or (
        np.ma.isMaskedArray(performance_source) and np.any(np.ma.getmaskarray(performance_source))
    ):
        raise ValueError("performance returns must be finite")
    if benchmark is not None and (
        not np.isfinite(benchmark).all()
        or (np.ma.isMaskedArray(benchmark_source) and np.any(np.ma.getmaskarray(benchmark_source)))
    ):
        raise ValueError("benchmark returns must be finite")

    embargo_evidence: object = embargo
    if isinstance(embargo_evidence, (bool, np.bool_)) or not isinstance(embargo_evidence, Integral):
        raise ValueError("embargo must be a nonnegative nonboolean integer")
    embargo = int(embargo_evidence)
    if embargo < 0:
        raise ValueError("embargo must be a nonnegative nonboolean integer")

    folds: list[PurgedCVFoldResult] = []
    hold_sharpes: list[float] = []
    for train_idx, test_idx in splits:
        train_idx = np.asarray(train_idx)
        test_idx = np.asarray(test_idx)
        for rows in (train_idx, test_idx):
            if rows.ndim != 1 or rows.dtype.kind not in "iu":
                raise ValueError("fold rows must be one-dimensional integers")
            if np.any(rows < 0) or np.any(rows >= n_obs):
                raise ValueError("fold index out of range for the performance matrix")
            if np.any(rows[1:] <= rows[:-1]):
                raise ValueError("fold rows must be unique and ascending")
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        if np.any(test_idx[1:] != test_idx[:-1] + 1):
            raise ValueError("test rows must form one contiguous fold")
        lower = int(test_idx[0]) - embargo
        upper = int(test_idx[-1]) + embargo
        if any(lower <= int(row) <= upper for row in train_idx):
            raise ValueError("train rows violate the declared embargo")
        if benchmark is not None:
            hold_sharpes.append(_sharpe(benchmark[test_idx]))
        train_sharpes = [_sharpe(performance[train_idx, c]) for c in range(performance.shape[1])]
        best = int(np.argmax(train_sharpes))
        folds.append(
            PurgedCVFoldResult(
                selected_config=best,
                oos_sharpe=_sharpe(performance[test_idx, best]),
                n_train=len(train_idx),
                n_test=len(test_idx),
            )
        )

    if not folds:
        raise ValueError("every fold was purged away — no fold could be evaluated")

    scores = np.array([f.oos_sharpe for f in folds], dtype=np.float64)
    return PurgedCVResult(
        n_folds=len(folds),
        embargo=embargo,
        folds=folds,
        mean_oos_sharpe=float(scores.mean()),
        oos_sharpe_std=float(scores.std(ddof=1)) if len(scores) > 1 else 0.0,
        consistency=float((scores > 0.0).mean()),
        mean_oos_hold_sharpe=float(np.mean(hold_sharpes)) if benchmark is not None else None,
    )
