"""Intrinsic forward evidence contracts shared by both score families (ADR-166)."""

from collections.abc import Sequence
from datetime import UTC, datetime
from itertools import pairwise
from math import isclose, isfinite


def forward_timestamp_utc(value: datetime) -> datetime:
    """Require an unambiguous forward evidence instant and retain it in UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("forward evidence timestamps must be timezone-aware")
    return value.astimezone(UTC)


def validate_forward_equities(values: Sequence[float]) -> None:
    """An equity index must represent finite strictly positive wealth."""
    if any(not isfinite(value) or value <= 0.0 for value in values):
        raise ValueError("forward equity values must be finite and positive")


def validate_forward_statistics(forward_bars: int, statistics: Sequence[float]) -> None:
    """Validate the existing intrinsic scalar constraints independently of a position."""
    if forward_bars < 0:
        raise ValueError("forward_bars must be non-negative")
    if not all(isfinite(value) for value in statistics):
        raise ValueError("forward statistics must be finite")


def validate_forward_curve(
    points: Sequence[tuple[datetime, float, float]],
    *,
    forward_bars: int,
    forward_return: float,
    benchmark_return: float,
    as_of: datetime,
) -> None:
    """Bind a measured curve to its counts, terminal returns, chronology, and cutoff.

    Empty legacy curves carry no geometry and remain explicitly supported.
    """
    if not points:
        return
    if len(points) != forward_bars:
        raise ValueError("forward equity length must match forward_bars")
    if any(current[0] <= previous[0] for previous, current in pairwise(points)):
        raise ValueError("forward equity timestamps must be strictly increasing")
    if points[-1][0] > as_of:
        raise ValueError("forward equity timestamps cannot follow as_of")
    terminal = points[-1]
    if not (
        isclose(terminal[1], 1.0 + forward_return, rel_tol=1e-9, abs_tol=1e-9)
        and isclose(terminal[2], 1.0 + benchmark_return, rel_tol=1e-9, abs_tol=1e-9)
    ):
        raise ValueError("forward equity terminal values must match score returns")
