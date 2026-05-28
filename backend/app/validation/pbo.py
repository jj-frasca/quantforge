from itertools import combinations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def _sharpe_per_config(block: FloatArray) -> FloatArray:
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1)
    sharpe: FloatArray = np.divide(mean, std, out=np.zeros_like(mean), where=std > 0)
    return sharpe


def probability_of_backtest_overfitting(
    performance: npt.NDArray[np.float64], n_splits: int = 10
) -> float:
    """PBO via Combinatorially-Symmetric Cross-Validation (Bailey et al. 2015).

    Args:
        performance: (T observations, N configurations) matrix of per-bar returns.
        n_splits: even number of row groups; uses all C(n_splits, n_splits/2) IS/OOS splits.

    Returns:
        Fraction of splits where the in-sample-best config lands below the OOS median — the
        probability of backtest overfitting, in [0, 1]. Pure noise -> ~0.5.
    """
    performance = np.asarray(performance, dtype=np.float64)
    n_obs, n_configs = performance.shape
    if n_configs < 2:
        raise ValueError("need >= 2 configurations")
    if n_splits < 2 or n_splits % 2 != 0:
        raise ValueError("n_splits must be even and >= 2")
    if n_obs < n_splits:
        raise ValueError("need at least n_splits observations")

    groups = np.array_split(np.arange(n_obs), n_splits)
    half = n_splits // 2
    overfit = 0
    total = 0

    for is_groups in combinations(range(n_splits), half):
        is_set = set(is_groups)
        is_rows = np.concatenate([groups[g] for g in is_groups])
        oos_rows = np.concatenate([groups[g] for g in range(n_splits) if g not in is_set])

        best = int(np.argmax(_sharpe_per_config(performance[is_rows])))
        oos_sharpe = _sharpe_per_config(performance[oos_rows])
        # rank of the IS-best config among OOS configs (0 = worst), as a fraction in (0, 1)
        oos_rank = int(np.argsort(np.argsort(oos_sharpe))[best])
        w = (oos_rank + 1) / (n_configs + 1)
        logit = np.log(w / (1.0 - w))

        overfit += int(logit <= 0.0)
        total += 1

    return overfit / total
