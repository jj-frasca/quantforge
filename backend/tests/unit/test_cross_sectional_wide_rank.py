"""Native wide score order must survive ranking (ADR-261 / FINDING-210)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.panel import long_short_weights


def _scale() -> np.longdouble:
    return np.sqrt(np.longdouble(np.finfo(np.longdouble).max))


def _native_weights(signals: pd.DataFrame, quantile: float) -> pd.DataFrame:
    """Independent stable scalar-order oracle; never converts scores to float."""
    expected = np.zeros(signals.shape)
    for row in range(len(signals)):
        valid = [col for col in range(signals.shape[1]) if not pd.isna(signals.iat[row, col])]
        if len(valid) < 2:
            continue
        ordered = sorted(valid, key=lambda col: signals.iat[row, col])
        size = max(1, int(quantile * len(valid)))
        expected[row, ordered[:size]] = -1.0 / size
        expected[row, ordered[-size:]] = 1.0 / size
    return pd.DataFrame(expected, index=signals.index, columns=signals.columns)


@pytest.mark.parametrize("case", ["large", "near_one", "negative", "small"])
@pytest.mark.parametrize("reverse", [False, True])
def test_long_short_weights_preserves_distinct_native_wide_order(case: str, reverse: bool) -> None:
    scale = _scale()
    if case == "large":
        values = [2 * scale, scale]
    elif case == "near_one":
        values = [np.longdouble(1) + np.finfo(np.longdouble).eps, np.longdouble(1)]
    elif case == "negative":
        values = [-scale, -2 * scale]
    else:
        values = [2 / scale, 1 / scale]
    signals = pd.DataFrame(np.array([values], dtype=np.longdouble), columns=["A", "B"])
    assert all(dtype == np.dtype(np.longdouble) for dtype in signals.dtypes)
    assert np.isfinite(signals.to_numpy()).all()
    assert signals.iat[0, 0] > signals.iat[0, 1]
    if reverse:
        signals = signals[["B", "A"]]
    with np.errstate(all="raise"):
        actual = long_short_weights(signals, 0.5)
    pd.testing.assert_frame_equal(actual, _native_weights(signals, 0.5), check_exact=True)


@pytest.mark.parametrize("quantile", [0.2, 0.5])
@pytest.mark.parametrize("reverse", [False, True])
def test_long_short_weights_preserves_wide_ties_missingness_and_caller_state(
    quantile: float, reverse: bool
) -> None:
    scale = _scale()
    signals = pd.DataFrame(
        np.array(
            [[2 * scale, scale, scale, np.nan], [np.nan] * 4, [1, np.nan, np.nan, np.nan]],
            dtype=np.longdouble,
        ),
        index=pd.date_range("2020-01-01", periods=3, tz="UTC"),
        columns=["A", "B", "C", "D"],
    )
    if reverse:
        signals = signals.loc[:, ::-1]
    before = signals.copy(deep=True)
    state = np.geterr()
    pd.testing.assert_frame_equal(
        long_short_weights(signals, quantile), _native_weights(signals, quantile), check_exact=True
    )
    pd.testing.assert_frame_equal(signals, before, check_exact=True)
    assert np.geterr() == state


@pytest.mark.parametrize("empty", ["rows", "columns"])
def test_long_short_weights_preserves_empty_wide_panels(empty: str) -> None:
    signals = pd.DataFrame(np.ones((2, 2), dtype=np.longdouble), columns=["A", "B"])
    signals = signals.iloc[:0] if empty == "rows" else signals.iloc[:, :0]
    pd.testing.assert_frame_equal(
        long_short_weights(signals), _native_weights(signals, 0.2), check_exact=True
    )


def test_long_short_weights_preserves_mixed_wide_nullable_order() -> None:
    signals = pd.DataFrame(
        {
            "A": np.array([2 * _scale(), np.nan], dtype=np.longdouble),
            "B": pd.Series([1.0, pd.NA], dtype="Float64"),
            "C": [0.0, np.nan],
        }
    )
    pd.testing.assert_frame_equal(
        long_short_weights(signals, 0.5), _native_weights(signals, 0.5), check_exact=True
    )


def test_portfolio_returns_uses_native_wide_score_order_on_next_bar() -> None:
    signals = pd.DataFrame(
        np.array([[2 * _scale(), _scale()]] * 2, dtype=np.longdouble), columns=["A", "B"]
    )
    prices = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 100.0]})
    actual = portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)
    np.testing.assert_allclose(actual, [-0.002, 0.1], rtol=1e-14, atol=0)


@given(
    coefficients=st.lists(st.integers(-4, 4), min_size=2, max_size=9),
    quantile=st.sampled_from([0.2, 0.5]),
    missing=st.booleans(),
)
def test_long_short_weights_matches_native_wide_stable_order_oracle(
    coefficients: list[int], quantile: float, missing: bool
) -> None:
    values = np.asarray(coefficients, dtype=np.longdouble) * _scale()
    signals = pd.DataFrame(np.stack([values, values[::-1]]))
    if missing:
        signals.iat[0, 0] = np.nan
    pd.testing.assert_frame_equal(
        long_short_weights(signals, quantile), _native_weights(signals, quantile), check_exact=True
    )
