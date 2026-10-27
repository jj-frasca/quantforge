"""Deterministic alternating-skew construction; no RNG or cohort execution (ADR-388)."""

from collections.abc import Sequence
from numbers import Integral

import numpy as np
from numpy.typing import NDArray


def alternating_skew_prices(codes: Sequence[int]) -> NDArray[np.float64]:
    """Return fixed-base prices for up to 7399 validated categorical transitions.

    Codes are nonboolean Integral 0/1/2 in a nontext Sequence; ndarray callers
    must materialize a sequence explicitly. Odd/even factors alternate conditional
    skew under ideal independent uniform categories, with ideal mean zero and
    variance 1/8192. Sequential native rounding is not an exact martingale.
    This pure kernel adopts no RNG, source archive, calendar or execution cohort.
    """
    if not isinstance(codes, Sequence) or isinstance(codes, (str, bytes, bytearray)):
        raise ValueError("codes must be a nontext Sequence of categorical integers")
    if len(codes) > 7399:
        raise ValueError("codes must contain at most 7399 transitions")
    original: tuple[object, ...] = tuple(codes)
    if len(original) > 7399:
        raise ValueError("codes must contain at most 7399 transitions")
    validated: list[int] = []
    for index, code in enumerate(original):
        if isinstance(code, bool) or not isinstance(code, Integral) or code not in (0, 1, 2):
            raise ValueError(f"codes[{index}] must be a nonboolean Integral in {{0, 1, 2}}")
        validated.append(int(code))
    normalized = tuple(validated)
    prices = np.empty(len(normalized) + 1, dtype=np.float64)
    price = 128.0
    prices[0] = price
    for index, code in enumerate(normalized, 1):
        if index % 2:
            factor = 65.0 / 64.0 if code == 0 else 127.0 / 128.0
        else:
            factor = 63.0 / 64.0 if code == 0 else 129.0 / 128.0
        price *= factor
        prices[index] = price
    return prices
