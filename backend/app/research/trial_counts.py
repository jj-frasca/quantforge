"""Original discrete trial-count evidence, before shortcuts or arithmetic (ADR-295)."""

from numbers import Integral
from typing import Literal


def require_trial_count(value: object, *, minimum: Literal[0, 1], parameter: str) -> int:
    """Accept integral scalars without coercion and avoid fixed-width addition."""
    domain = "positive" if minimum == 1 else "nonnegative"
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{parameter} must be a {domain} nonboolean integer")
    count = int(value)
    if count < minimum:
        raise ValueError(f"{parameter} must be a {domain} nonboolean integer")
    return count
