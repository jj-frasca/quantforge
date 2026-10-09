"""Original cost evidence must be valid before reference shortcuts (ADR-232)."""

from fractions import Fraction
from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import (
    ar1_conditional_mean_sign_sharpe,
    oracle_sharpe,
    oracle_sharpe_of,
)

ENTRIES = ["generic", "historical", "explicit-ar"]
CLOSES = [100.0, 101.0, 100.0, 101.0, 100.0]


def score(entry: str, cost: object, n: int = 5) -> float:
    data = pd.DataFrame({"close": pd.Series(CLOSES[:n], dtype=float)})
    if entry == "generic":
        return oracle_sharpe_of(data, pd.Series(1.0, index=data.index), cost_rate=cost)
    if entry == "historical":
        return oracle_sharpe(data, phi=-0.3, cost_rate=cost)
    return ar1_conditional_mean_sign_sharpe(data, phi=-0.3, drift=0.0, cost_rate=cost)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("n", [0, 3, 5])
@pytest.mark.parametrize(
    "cost",
    [True, False, np.bool_(True), np.bool_(False), np.nan, np.inf, -np.inf, "0.001", 1j, None],
)
def test_reference_invalid_original_cost_is_refused_before_shortcut(
    entry: str, n: int, cost: object
) -> None:
    with pytest.raises(ValueError):
        score(entry, cost, n)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("n", [0, 3, 5])
def test_reference_nonrepresentable_cost_is_refused(entry: str, n: int) -> None:
    with pytest.raises(ValueError, match="finite float-representable"):
        score(entry, 10**400, n)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("cost", [-0.001, Fraction(-1, 10**400)])
def test_reference_original_negative_cost_remains_refused(entry: str, cost: object) -> None:
    with pytest.raises(ValueError, match="cost_rate must be >= 0"):
        score(entry, cost, 3)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("cost", [0.0, 0.001, np.float32(0.001), np.float64(0.001), np.int64(1)])
def test_reference_valid_cost_preserves_exact_native_operand(entry: str, cost: object) -> None:
    data = pd.DataFrame({"close": CLOSES})
    returns = data["close"].pct_change().dropna()
    position = (
        pd.Series(1.0, index=returns.index)
        if entry == "generic"
        else np.sign(-0.3 * returns.shift(1)).fillna(0.0)
    )
    earned = position * returns - position.diff().abs().fillna(position.abs()) * cost
    expected = float(np.sqrt(252) * earned.mean() / earned.std())
    assert score(entry, cost) == expected


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("n", [0, 3])
def test_reference_complete_short_prices_with_finite_cost_retain_zero(entry: str, n: int) -> None:
    assert score(entry, 1e308, n) == 0.0


@given(st.floats(min_value=0.0, max_value=0.1, allow_nan=False), st.sampled_from(ENTRIES))
def test_reference_ordinary_cost_matches_independent_scalar_turnover(
    cost: float, entry: str
) -> None:
    returns = [right / left - 1.0 for left, right in pairwise(CLOSES)]
    positions = (
        [1.0] * len(returns)
        if entry == "generic"
        else [0.0, *[float(np.sign(-0.3 * lag)) for lag in returns[:-1]]]
    )
    previous = 0.0
    earned = []
    for position, realized in zip(positions, returns, strict=True):
        earned.append(position * realized - abs(position - previous) * cost)
        previous = position
    expected = float(np.sqrt(252) * np.mean(earned) / np.std(earned, ddof=1))
    assert score(entry, cost) == pytest.approx(expected, rel=1e-12, abs=1e-12)
