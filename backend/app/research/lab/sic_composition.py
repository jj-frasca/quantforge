"""Pure statistics for the ADR-161 SIC-division composition test (single look, read-only)."""

from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any, NamedTuple

import numpy as np

SEED = 20261004
MIN_DIVISION_SIZE = 5
_RANGES = (
    (1, 9, "A"),
    (10, 14, "B"),
    (15, 17, "C"),
    (20, 39, "D"),
    (40, 49, "E"),
    (50, 51, "F"),
    (52, 59, "G"),
    (60, 67, "H"),
    (70, 89, "I"),
    (91, 99, "J"),
)


class Member(NamedTuple):
    division: str
    value: float


def sic_division(code: str | None) -> str | None:
    if code is None or len(code) != 4 or not code.isdigit():
        return None
    major = int(code[:2])
    for low, high, label in _RANGES:
        if low <= major <= high:
            return label
    return None


def collapse(a: Sequence[Member], b: Sequence[Member]) -> tuple[list[Member], list[Member]]:
    """Merge divisions with fewer than MIN_DIVISION_SIZE symbols across both cohorts into Other."""
    counts = Counter(m.division for m in [*a, *b])
    small = {d for d, n in counts.items() if n < MIN_DIVISION_SIZE}

    def relabel(members: Sequence[Member]) -> list[Member]:
        return [Member("Other" if m.division in small else m.division, m.value) for m in members]

    return relabel(a), relabel(b)


def _by_division(members: Sequence[Member]) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for m in members:
        grouped[m.division].append(m.value)
    return grouped


def post_stratified_mean(source: Sequence[Member], target: Sequence[Member]) -> float:
    """`source`'s division means weighted by `target`'s division shares, over shared divisions."""
    src, tgt = _by_division(source), Counter(m.division for m in target)
    shared = [d for d in tgt if d in src]
    total = sum(tgt[d] for d in shared)
    return float(sum(tgt[d] / total * np.mean(src[d]) for d in shared))


def _chi_square(divs: np.ndarray, is_a: np.ndarray) -> float:
    stat = 0.0
    n_a, n = int(is_a.sum()), len(divs)
    for d in np.unique(divs):
        in_d = divs == d
        for cohort_size, mask in ((n_a, is_a), (n - n_a, ~is_a)):
            expected = in_d.sum() * cohort_size / n
            stat += (int((in_d & mask).sum()) - expected) ** 2 / expected
    return stat


def _bootstrap(members: Sequence[Member], rng: np.random.Generator) -> list[Member]:
    out: list[Member] = []
    for d, values in _by_division(members).items():
        arr = np.asarray(values)
        out.extend(Member(d, float(v)) for v in rng.choice(arr, size=len(arr), replace=True))
    return out


def _mean(members: Sequence[Member]) -> float:
    return float(np.mean([m.value for m in members]))


def classify(
    raw_ci: tuple[float, float],
    s1_p: float,
    adjusted_ci: tuple[float, float],
    *,
    raw: float,
    adjusted: float,
) -> str:
    raw_excludes = raw_ci[0] > 0 or raw_ci[1] < 0
    adj_excludes = adjusted_ci[0] > 0 or adjusted_ci[1] < 0
    if raw_excludes and s1_p < 0.05 and not adj_excludes and abs(adjusted) <= 0.5 * abs(raw):
        return "explains"
    if (
        raw_excludes
        and adj_excludes
        and np.sign(adjusted) == np.sign(raw)
        and abs(adjusted) >= 0.5 * abs(raw)
    ):
        return "does_not_explain"
    return "inconclusive"


def run_test(a: Sequence[Member], b: Sequence[Member], *, draws: int = 10_000) -> dict[str, Any]:
    """a = 7,400-bar cohort, b = 9,247-bar cohort. Gap is mean(a) - mean(b)."""
    a, b = collapse(a, b)
    rng = np.random.default_rng(SEED)
    divs = np.array([m.division for m in [*a, *b]])
    is_a = np.array([True] * len(a) + [False] * len(b))
    observed = _chi_square(divs, is_a)
    exceed = sum(_chi_square(divs, rng.permutation(is_a)) >= observed for _ in range(draws))
    s1_p = (exceed + 1) / (draws + 1)

    raw = _mean(a) - _mean(b)
    adjusted = _mean(a) - post_stratified_mean(b, a)
    raws, adjs = [], []
    for _ in range(draws):
        ra, rb = _bootstrap(a, rng), _bootstrap(b, rng)
        raws.append(_mean(ra) - _mean(rb))
        adjs.append(_mean(ra) - post_stratified_mean(rb, ra))
    raw_ci = (float(np.percentile(raws, 2.5)), float(np.percentile(raws, 97.5)))
    adj_ci = (float(np.percentile(adjs, 2.5)), float(np.percentile(adjs, 97.5)))
    return {
        "n": {"a": len(a), "b": len(b)},
        "means": {"a": _mean(a), "b": _mean(b)},
        "s1_chi_square": observed,
        "s1_p": s1_p,
        "raw_gap": raw,
        "raw_gap_ci": raw_ci,
        "adjusted_gap": adjusted,
        "adjusted_gap_ci": adj_ci,
        "reading": classify(raw_ci, s1_p, adj_ci, raw=raw, adjusted=adjusted),
    }
