"""Original close observations cannot disappear into reference scores (ADR-230)."""

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


def score(closes: pd.Series, entry: str) -> float:
    data = pd.DataFrame({"close": closes})
    if entry == "generic":
        return oracle_sharpe_of(data, pd.Series(1.0, index=data.index))
    if entry == "historical":
        return oracle_sharpe(data, phi=-0.3)
    return ar1_conditional_mean_sign_sharpe(data, phi=-0.3, drift=0.0)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -100.0])
@pytest.mark.parametrize("location", [0, 2, 4])
def test_reference_invalid_close_is_refused_before_returns(
    entry: str, bad: float, location: int
) -> None:
    closes = pd.Series([100.0, 101.0, 100.0, 101.0, 100.0])
    closes.iloc[location] = bad
    with pytest.raises(ValueError, match=r"prices.*positive.*finite"):
        score(closes, entry)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -100.0])
def test_reference_invalid_singleton_is_not_a_measured_zero(entry: str, bad: float) -> None:
    with pytest.raises(ValueError, match=r"prices.*positive.*finite"):
        score(pd.Series([bad]), entry)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("dtype", ["bool", "complex128", "object", "str"])
def test_reference_nonreal_price_dtype_is_refused(entry: str, dtype: str) -> None:
    closes = pd.Series([1, 2, 1, 2, 1], dtype=dtype)
    with pytest.raises(ValueError, match=r"prices.*real nonboolean numeric"):
        score(closes, entry)


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("dtype", ["float64", "Float64", "int64", "Int64", "uint64"])
def test_reference_complete_numeric_prices_keep_native_score(entry: str, dtype: str) -> None:
    closes = pd.Series([100, 101, 100, 101, 100], dtype=dtype)
    returns = closes.pct_change().dropna()
    if entry == "generic":
        position = pd.Series(1.0, index=returns.index)
    else:
        position = np.sign(-0.3 * returns.shift(1)).fillna(0.0)
    realized = position * returns
    expected = float(np.sqrt(252) * realized.mean() / realized.std())
    assert score(closes, entry) == expected


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("closes", [[], [100.0], [100.0, 101.0], [100.0] * 5])
def test_reference_complete_short_empty_constant_prices_retain_zero(
    entry: str, closes: list[float]
) -> None:
    assert score(pd.Series(closes, dtype=float), entry) == 0.0


@pytest.mark.parametrize("entry", ENTRIES)
def test_reference_missing_nullable_price_is_refused(entry: str) -> None:
    with pytest.raises(ValueError, match=r"prices.*positive.*finite"):
        score(pd.Series([100, 101, None, 100, 101], dtype="Float64"), entry)


@given(
    st.lists(st.floats(min_value=1, max_value=1000, allow_nan=False), min_size=1, max_size=30),
    st.integers(min_value=0, max_value=29),
    st.sampled_from(ENTRIES),
)
def test_reference_missing_price_never_becomes_a_measurement(
    prices: list[float], offset: int, entry: str
) -> None:
    closes = pd.Series(prices)
    closes.iloc[offset % len(closes)] = np.nan
    with pytest.raises(ValueError, match=r"prices.*positive.*finite"):
        score(closes, entry)
