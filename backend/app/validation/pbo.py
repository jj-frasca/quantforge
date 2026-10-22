from itertools import combinations

import numpy as np
import numpy.typing as npt
from scipy.stats import rankdata

FloatArray = npt.NDArray[np.float64]


def _sharpe_from_exact_float64_translation(block: FloatArray, mean: FloatArray) -> FloatArray:
    """Center certified exact differences, retaining native block means (ADR-289)."""
    with np.errstate(all="ignore"):
        differences = block - block[0]
        scale = np.max(np.abs(differences), axis=0)
        normalized_std = (differences / scale).std(axis=0, ddof=1)
        mean_mantissa, mean_exponent = np.frexp(mean)
        scale_mantissa, scale_exponent = np.frexp(scale)
        scores: FloatArray = np.ldexp(
            mean_mantissa / scale_mantissa / normalized_std,
            mean_exponent - scale_exponent,
        )
    if not np.isfinite(scores).all():
        raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
    return scores


def _sharpe_per_config(block: FloatArray, *, exact_translation: bool = True) -> FloatArray:
    constant = np.all(block == block[0], axis=0)
    sharpe: FloatArray = np.zeros(block.shape[1], dtype=np.float64)
    if constant.all():
        return sharpe
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        mean = block.mean(axis=0)
        std = block.std(axis=0, ddof=1)
        if (
            not np.isfinite(mean[~constant]).all()
            or not np.isfinite(std[~constant]).all()
            or np.any(std[~constant] <= 0)
        ):
            raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
        np.divide(mean, std, out=sharpe, where=~constant)
    if not np.isfinite(sharpe).all():
        raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
    if exact_translation:
        with np.errstate(all="ignore"):
            minimum = block.min(axis=0)
            maximum = block.max(axis=0)
            minimum_magnitude = np.minimum(np.abs(minimum), np.abs(maximum))
            maximum_magnitude = np.maximum(np.abs(minimum), np.abs(maximum))
            # Sterbenz's inclusive factor-two range certifies exact subtraction.
            eligible = (
                ~constant
                & (mean != 0)
                & ((minimum > 0) | (maximum < 0))
                & (maximum_magnitude <= 2 * minimum_magnitude)
            )
            if eligible.any():
                sharpe[eligible] = _sharpe_from_exact_float64_translation(
                    block[:, eligible], mean[eligible]
                )
    return sharpe


def probability_of_backtest_overfitting(
    performance: npt.NDArray[np.float64], n_splits: int = 10
) -> float:
    """PBO via Combinatorially-Symmetric Cross-Validation (Bailey et al. 2015).

    Args:
        performance: (T observations, N configurations) matrix of per-bar returns.
        n_splits: even number of row groups; uses all C(n_splits, n_splits/2) IS/OOS splits.

    Returns:
        Mean across splits of the equally weighted tied IS winners' indicators that their
        average one-based OOS rank divided by (N + 1) is <= 0.5 (ADR-105), in [0, 1].
        There is no universal noise value: supplied candidate dependence and ties matter.
        With tie-free exchangeable OOS ranks and IS selection independent of OOS ordering,
        the selected rank is uniform and expected PBO is floor((N + 1) / 2) / N.
        This is an expectation, not a guarantee for one matrix; identical candidates give 1.
    """
    performance_source = performance
    source = np.asarray(performance)
    if source.ndim != 2:
        raise ValueError("performance must be a two-dimensional matrix")
    if source.dtype.kind not in {"i", "u", "f"}:
        raise ValueError("performance must contain real nonboolean numeric returns")
    original_float64 = source.dtype.kind == "f" and source.dtype.itemsize == 8
    performance = np.asarray(source, dtype=np.float64)
    n_obs, n_configs = performance.shape
    if n_configs < 2:
        raise ValueError("need >= 2 configurations")
    if n_splits < 2 or n_splits % 2 != 0:
        raise ValueError("n_splits must be even and >= 2")
    if n_obs < n_splits:
        raise ValueError("need at least n_splits observations")
    if n_obs // 2 < 2:
        raise ValueError("each balanced half needs at least two observations")
    if not np.isfinite(performance).all() or (
        np.ma.isMaskedArray(performance_source) and np.any(np.ma.getmaskarray(performance_source))
    ):
        raise ValueError("performance must contain only finite returns")

    groups = np.array_split(np.arange(n_obs), n_splits)
    half = n_splits // 2
    overfit = 0.0
    total = 0

    # Every subset of `half` groups appears twice across the C(n, n/2) splits — once in-sample and
    # once, as the complement of another split, out-of-sample. Scoring each subset once halves the
    # work exactly, and PBO is 40% of a search's runtime. Memoized rather than restructured because
    # the identity is between splits, not within one.
    cache: dict[tuple[int, ...], FloatArray] = {}

    def sharpe_for(subset: tuple[int, ...]) -> FloatArray:
        cached = cache.get(subset)
        if cached is None:
            rows = np.concatenate([groups[g] for g in subset])
            cached = _sharpe_per_config(performance[rows], exact_translation=original_float64)
            cache[subset] = cached
        return cached

    for is_groups in combinations(range(n_splits), half):
        is_set = set(is_groups)
        oos_groups = tuple(g for g in range(n_splits) if g not in is_set)

        is_sharpe = sharpe_for(is_groups)
        best = np.flatnonzero(is_sharpe == is_sharpe.max())
        oos_sharpe = sharpe_for(oos_groups)
        # ADR-105: tied OOS values receive the midpoint of their occupied one-based ranks. Every
        # tied IS maximum contributes equally, which is the expectation under uniform selection
        # among indistinguishable winners and cannot change when candidate columns are permuted.
        oos_ranks = rankdata(oos_sharpe, method="average")
        w = oos_ranks[best] / (n_configs + 1)
        logits = np.log(w / (1.0 - w))

        overfit += float(np.mean(logits <= 0.0))
        total += 1

    return overfit / total
