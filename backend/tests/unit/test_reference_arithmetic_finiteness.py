"""Reference arithmetic cannot turn finite-input overflow into measured scores (ADR-229)."""

import numpy as np
import pandas as pd
import pytest

from app.research.lab.calibration import (
    ar1_conditional_mean_sign_sharpe,
    oracle_sharpe,
    oracle_sharpe_of,
)


def frame(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": closes}, index=pd.date_range("2020-01-01", periods=len(closes)))


def score(data: pd.DataFrame, entry: str, cost: float, *, phi: float = -0.3) -> float:
    if entry == "generic":
        returns = data["close"].pct_change().dropna()
        return oracle_sharpe_of(data, phi * returns.shift(1), cost_rate=cost)
    if entry == "historical":
        return oracle_sharpe(data, phi=phi, cost_rate=cost)
    return ar1_conditional_mean_sign_sharpe(data, phi=phi, drift=0.0, cost_rate=cost)


@pytest.mark.parametrize("entry", ["generic", "historical", "explicit-ar"])
@pytest.mark.parametrize("cost", [1e200, 1e308])
def test_finite_cost_derived_overflow_is_refused(entry: str, cost: float) -> None:
    data = frame([100.0, 101.0, 100.0, 101.0, 100.0])
    with pytest.raises(ValueError, match="finite"):
        score(data, entry, cost)


@pytest.mark.parametrize("entry", ["generic", "historical", "explicit-ar"])
@pytest.mark.parametrize("cost", [0.0, 0.001, 100.0])
def test_ordinary_reference_score_matches_original_native_arithmetic_exactly(
    entry: str,
    cost: float,
) -> None:
    data = frame([100.0, 101.0, 100.0, 101.0, 100.0])
    returns = data["close"].pct_change().dropna()
    position = pd.Series([0.0, -1.0, 1.0, -1.0], index=returns.index)
    turnover = pd.Series([0.0, 1.0, 2.0, 2.0], index=returns.index)
    earned = position * returns - turnover * cost
    expected = float(np.sqrt(252) * earned.mean() / earned.std(ddof=1))
    assert score(data, entry, cost) == expected


@pytest.mark.parametrize("entry", ["generic", "historical", "explicit-ar"])
def test_genuine_finite_zero_variance_remains_zero(entry: str) -> None:
    assert score(frame([100.0] * 5), entry, 0.0) == 0.0
    assert score(frame([100.0, 101.0, 100.0, 101.0, 100.0]), entry, 1e308, phi=0.0) == 0.0


@pytest.mark.parametrize("entry", ["generic", "historical", "explicit-ar"])
def test_short_history_still_has_no_reference_score(entry: str) -> None:
    assert score(frame([100.0, 101.0, 100.0]), entry, 1e308) == 0.0


def test_missing_conditional_means_keep_the_existing_flat_startup_convention() -> None:
    data = frame([100.0, 101.0, 100.0, 101.0, 100.0])
    missing = pd.Series(np.nan, index=data.index)
    assert oracle_sharpe_of(data, missing, cost_rate=1e308) == 0.0
