import math

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.research.backtesting.metrics import TRADING_DAYS
from app.validation.result_graph import FrozenResultList

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

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    selected_config: int = Field(ge=0)
    is_sharpe: float = Field(allow_inf_nan=False)
    oos_sharpe: float = Field(allow_inf_nan=False)
    n_train: int = Field(ge=1)
    n_test: int = Field(ge=1)


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

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    n_splits: int = Field(ge=1)
    splits: list[WalkForwardSplitResult]
    mean_is_sharpe: float = Field(allow_inf_nan=False)
    mean_oos_sharpe: float = Field(allow_inf_nan=False)
    consistency: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    efficiency: float | None = Field(default=None, allow_inf_nan=False)
    # ADR-068: buy-and-hold scored across the SAME test blocks. `mean_oos_sharpe` is denominated in
    # the drift of the series it was computed on — on data with no edge by construction it comes
    # out at the underlying's own buy-and-hold Sharpe — so the two are only interpretable together.
    # None means no benchmark was supplied, which is not a benchmark of zero (ADR-067).
    mean_oos_hold_sharpe: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _bind_summary_to_splits(self) -> "WalkForwardResult":
        if len(self.splits) != self.n_splits:
            raise ValueError("n_splits must equal len(splits)")
        mean_is = sum(split.is_sharpe for split in self.splits) / self.n_splits
        mean_oos = sum(split.oos_sharpe for split in self.splits) / self.n_splits
        consistency = sum(split.oos_sharpe > 0.0 for split in self.splits) / self.n_splits
        expected_efficiency = mean_oos / mean_is if mean_is > 0.0 else None
        for name, actual, expected in (
            ("mean_is_sharpe", self.mean_is_sharpe, mean_is),
            ("mean_oos_sharpe", self.mean_oos_sharpe, mean_oos),
            ("consistency", self.consistency, consistency),
        ):
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{name} must agree with splits")
        if expected_efficiency is None:
            if self.efficiency is not None:
                raise ValueError(
                    "efficiency must be null when mean in-sample Sharpe is not positive"
                )
        elif self.efficiency is None or not math.isclose(
            self.efficiency, expected_efficiency, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("efficiency must agree with split means")
        object.__setattr__(self, "splits", FrozenResultList(list(self.splits)))
        return self


def _sharpe(returns: FloatArray) -> float:
    """Annualized, matching metrics.sharpe_ratio — these numbers sit next to the observed and
    holdout Sharpes, so a per-bar figure would read as a sqrt(252)x weaker result."""
    if len(returns) < 2:
        return 0.0
    std = float(returns.std(ddof=1))
    return float(np.sqrt(TRADING_DAYS) * returns.mean() / std) if std > 0 else 0.0


def walk_forward_evaluate(
    performance: FloatArray,
    splits: list[tuple[IntArray, IntArray]],
    *,
    benchmark: FloatArray | None = None,
) -> WalkForwardResult:
    """Select the best config on each train block, score it on the following test block (ADR-038).

    Args:
        performance: (T observations, N configurations) matrix of per-bar returns — the same matrix
            PBO consumes. Slicing it is equivalent to re-running the window because every catalog
            strategy is causal (signal at t uses bars <= t only); see ADR-038.
        splits: expanding-window splits from ``walk_forward_splits``.
        benchmark: optional per-bar buy-and-hold returns for the same window, scored across the
            same test blocks (ADR-068). Pairing it here rather than at the call site is the point:
            a benchmark measured over a different window is the confound it exists to remove.

    Returns:
        A ``WalkForwardResult``. Ties in the train-block argmax resolve to the lowest config index,
        so the result is deterministic.
    """
    performance_source = performance
    benchmark_source = benchmark
    performance = np.asarray(performance)
    if performance.ndim != 2 or performance.shape[1] < 2:
        raise ValueError("need >= 2 configurations to walk a selection forward")
    if not splits:
        raise ValueError("need >= 1 split")

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
    results: list[WalkForwardSplitResult] = []
    for train_idx, test_idx in splits:
        train_idx = np.asarray(train_idx)
        test_idx = np.asarray(test_idx)
        for rows in (train_idx, test_idx):
            if rows.ndim != 1 or rows.size == 0 or rows.dtype.kind not in "iu":
                raise ValueError("split rows must be nonempty one-dimensional integers")
            if np.any(rows < 0) or np.any(rows >= n_obs):
                raise ValueError("split index out of range for the performance matrix")
            if np.any(rows[1:] <= rows[:-1]):
                raise ValueError("split rows must be unique and ascending")
        if train_idx[-1] >= test_idx[0]:
            raise ValueError("train rows must precede test rows")
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
        mean_oos_hold_sharpe=(
            None
            if benchmark is None
            else float(np.mean([_sharpe(benchmark[test_idx]) for _, test_idx in splits]))
        ),
    )
