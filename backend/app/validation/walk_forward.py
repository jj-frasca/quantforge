import numpy as np
import numpy.typing as npt

IntArray = npt.NDArray[np.intp]


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
