"""A positional reference lag must respect source index ordering (ADR-231)."""

from typing import Any

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


def score(data: pd.DataFrame, entry: str, cost: float = 0.0) -> float:
    if entry == "generic":
        return oracle_sharpe_of(data, pd.Series(1.0, index=data.index[1:]), cost_rate=cost)
    if entry == "historical":
        return oracle_sharpe(data, phi=-0.3, cost_rate=cost)
    return ar1_conditional_mean_sign_sharpe(data, phi=-0.3, drift=0.0, cost_rate=cost)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("labels", [[1, 3, 2, 4, 5], [1, 2, 2, 3, 4], [2, 1], [1, 1]])
@pytest.mark.parametrize("datetime_index", [False, True])
def test_reference_unordered_duplicate_source_calendar_is_refused(
    entry: str, labels: list[int], datetime_index: bool
) -> None:
    index: Any = (
        pd.to_datetime([f"2020-01-{day:02d}" for day in labels]) if datetime_index else labels
    )
    data = pd.DataFrame({"close": [100.0, 121.0, 110.0, 115.0, 112.0][: len(labels)]}, index=index)
    with pytest.raises(ValueError, match="calendar must be unique and ascending"):
        score(data, entry)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("cost", [0.0, 0.001])
@pytest.mark.parametrize("calendar", ["integer", "naive", "utc", "offset"])
def test_reference_ordered_calendar_preserves_exact_native_score(
    entry: str, cost: float, calendar: str
) -> None:
    data = pd.DataFrame({"close": [100.0, 121.0, 110.0, 115.0, 112.0]})
    returns = data["close"].pct_change().dropna()
    position = (
        pd.Series(1.0, index=returns.index)
        if entry == "generic"
        else np.sign(-0.3 * returns.shift(1)).fillna(0.0)
    )
    realized = position * returns - position.diff().abs().fillna(position.abs()) * cost
    expected = float(np.sqrt(252) * realized.mean() / realized.std())
    if calendar == "integer":
        data.index = pd.Index([2, 4, 8, 16, 32])
    else:
        timezone = {"naive": None, "utc": "UTC", "offset": "Etc/GMT+7"}[calendar]
        data.index = pd.date_range("2020-01-01", periods=5, tz=timezone)
    assert score(data, entry, cost) == expected


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("n", [0, 1, 2])
def test_reference_ordered_short_calendar_retains_zero(entry: str, n: int) -> None:
    data = pd.DataFrame({"close": pd.Series([100.0] * n, dtype=float)})
    assert score(data, entry) == 0.0


@given(st.permutations([0, 1, 2, 3, 4]), st.sampled_from(ENTRIES))
def test_reference_nonidentity_source_permutation_is_refused(order: list[int], entry: str) -> None:
    data = pd.DataFrame({"close": [100.0, 121.0, 110.0, 115.0, 112.0]}).iloc[order]
    if list(order) == [0, 1, 2, 3, 4]:
        assert np.isfinite(score(data, entry))
    else:
        with pytest.raises(ValueError, match="calendar must be unique and ascending"):
            score(data, entry)
