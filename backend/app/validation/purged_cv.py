import numpy as np
import numpy.typing as npt

IntArray = npt.NDArray[np.intp]


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
