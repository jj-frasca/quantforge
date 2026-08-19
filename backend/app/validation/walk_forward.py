import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

IntArray = npt.NDArray[np.intp]
FloatArray = npt.NDArray[np.float64]


def walk_forward_splits(
    n_obs: int, n_splits: int, min_train: int | None = None
) -> list[tuple[IntArray, IntArray]]:
    """Expanding-window walk-forward index splits (validation-methodology.md §3).

    Notes:
        Each split trains on [0, k) and tests on the next forward block, so
        max(train) < min(test) always — never uses future data. The final test block absorbs
        any remainder.
    """
    if n_splits < 1:
        raise ValueError("n_splits must be >= 1")
    if n_obs < n_splits + 1:
        raise ValueError("n_obs must be >= n_splits + 1")

    fold = n_obs // (n_splits + 1)  # >= 1 given the n_obs >= n_splits + 1 guard above
    base = min_train if min_train is not None else fold
    if base < 1:
        raise ValueError("min_train must be >= 1")
    # The last split trains on [0, base + (n_splits-1)*fold); leave room for a non-empty test.
    if base + (n_splits - 1) * fold >= n_obs:
        raise ValueError(
            "min_train too large for n_obs / n_splits (would leave an empty test fold)"
        )

    splits: list[tuple[IntArray, IntArray]] = []
    for i in range(n_splits):
        train_end = base + i * fold
        test_end = n_obs if i == n_splits - 1 else train_end + fold
        train_idx = np.arange(0, train_end, dtype=np.intp)
        test_idx = np.arange(train_end, test_end, dtype=np.intp)
        splits.append((train_idx, test_idx))
    return splits


class WalkForwardSplitResult(BaseModel):
    """One walk-forward window: what was selected on the train block, and how it then did."""

    model_config = ConfigDict(frozen=True)

    selected_config: int
    is_sharpe: float
    oos_sharpe: float
    n_train: int
    n_test: int


class WalkForwardResult(BaseModel):
    """Prequential out-of-sample estimate for the SELECTION PROCEDURE (ADR-038).

    Notes:
        The locked holdout (ADR-016) scores one config that was chosen using the whole search set.
        This scores the act of re-choosing: select on what you had, measure what came next, repeat.
        ``mean_oos_sharpe`` and ``consistency`` are the headline numbers; ``efficiency`` (Pardo's
        walk-forward efficiency) is undefined when the in-sample mean is not positive, because a
        ratio of two negative Sharpes is positive and would read as "efficient" while both halves
        lost money. Diagnostic only — nothing gates on it (ADR-038 §"Why not a gate — yet").
    """

    model_config = ConfigDict(frozen=True)

    n_splits: int
    splits: list[WalkForwardSplitResult]
    mean_is_sharpe: float
    mean_oos_sharpe: float
    consistency: float
    efficiency: float | None = None


def _sharpe(returns: FloatArray) -> float:
    if len(returns) < 2:
        return 0.0
    std = float(returns.std(ddof=1))
    return float(returns.mean() / std) if std > 0 else 0.0


def walk_forward_evaluate(
    performance: FloatArray, splits: list[tuple[IntArray, IntArray]]
) -> WalkForwardResult:
    """Select the best config on each train block, score it on the following test block (ADR-038).

    Args:
        performance: (T observations, N configurations) matrix of per-bar returns — the same matrix
            PBO consumes. Slicing it is equivalent to re-running the window because every catalog
            strategy is causal (signal at t uses bars <= t only); see ADR-038.
        splits: expanding-window splits from ``walk_forward_splits``.

    Returns:
        A ``WalkForwardResult``. Ties in the train-block argmax resolve to the lowest config index,
        so the result is deterministic.
    """
    performance = np.asarray(performance, dtype=np.float64)
    if performance.ndim != 2 or performance.shape[1] < 2:
        raise ValueError("need >= 2 configurations to walk a selection forward")
    if not splits:
        raise ValueError("need >= 1 split")

    n_obs = performance.shape[0]
    results: list[WalkForwardSplitResult] = []
    for train_idx, test_idx in splits:
        if int(train_idx.max()) >= n_obs or int(test_idx.max()) >= n_obs:
            raise ValueError("split index out of range for the performance matrix")
        train_sharpes = [_sharpe(performance[train_idx, c]) for c in range(performance.shape[1])]
        best = int(np.argmax(train_sharpes))
        results.append(
            WalkForwardSplitResult(
                selected_config=best,
                is_sharpe=train_sharpes[best],
                oos_sharpe=_sharpe(performance[test_idx, best]),
                n_train=len(train_idx),
                n_test=len(test_idx),
            )
        )

    mean_is = float(np.mean([r.is_sharpe for r in results]))
    mean_oos = float(np.mean([r.oos_sharpe for r in results]))
    return WalkForwardResult(
        n_splits=len(results),
        splits=results,
        mean_is_sharpe=mean_is,
        mean_oos_sharpe=mean_oos,
        consistency=sum(r.oos_sharpe > 0.0 for r in results) / len(results),
        efficiency=(mean_oos / mean_is) if mean_is > 0.0 else None,
    )
