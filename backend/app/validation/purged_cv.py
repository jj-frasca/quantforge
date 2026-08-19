from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from app.research.backtesting.metrics import TRADING_DAYS
from app.research.strategies.base import BaseStrategy

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

    model_config = ConfigDict(frozen=True)

    selected_config: int
    oos_sharpe: float
    n_train: int
    n_test: int


class PurgedCVResult(BaseModel):
    """Leakage-controlled out-of-sample dispersion of an edge across folds (ADR-039).

    Notes:
        NOT a live-simulation estimate: a fold's training rows include indices AFTER its test
        block, so selection sees the future. That is what the technique buys — many resampled
        paths with boundary leakage purged. ADR-038's walk-forward is the causal counterpart;
        a large gap between the two is itself diagnostic. Sharpes are annualized, matching
        metrics.sharpe_ratio. Diagnostic only — nothing gates on it.
    """

    model_config = ConfigDict(frozen=True)

    n_folds: int
    embargo: int
    folds: list[PurgedCVFoldResult]
    mean_oos_sharpe: float
    oos_sharpe_std: float
    consistency: float


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
    performance: FloatArray, splits: list[tuple[IntArray, IntArray]], *, embargo: int
) -> PurgedCVResult:
    """Select on each fold's purged train rows, score that choice on the fold (ADR-039).

    Args:
        performance: (T observations, N configurations) per-bar returns — the matrix PBO consumes.
        splits: purged K-fold splits from ``purged_kfold_splits``.
        embargo: the embargo those splits were built with, recorded on the result so a stored
            measurement says how hard it was actually purged.

    Notes:
        A fold whose training set was purged away entirely has nothing to select on and is
        DROPPED, not scored — counting it would report a selection that never happened. Every
        fold being unusable is an error, not an empty result.
    """
    performance = np.asarray(performance, dtype=np.float64)
    if performance.ndim != 2 or performance.shape[1] < 2:
        raise ValueError("need >= 2 configurations to select within a fold")
    if not splits:
        raise ValueError("need >= 1 fold")

    folds: list[PurgedCVFoldResult] = []
    for train_idx, test_idx in splits:
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
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
    )
