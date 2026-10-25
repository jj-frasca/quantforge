"""ADR-370: count arithmetic must preserve momentum's causal price shifts."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.engine import BacktestEngine
from app.research.strategies.momentum import MomentumStrategy


def _frame() -> pd.DataFrame:
    rows = np.arange(300)
    return pd.DataFrame(
        {"close": 100.0 + 0.01 * rows + 0.1 * np.sin(rows)},
        index=pd.date_range("2020-01-01", periods=300, tz="UTC"),
    )


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
@pytest.mark.parametrize("dtype,lookback", [(np.int8, 127), (np.uint8, 255)])
def test_momentum_wrapping_counts_match_mathematical_python_shift(
    policy: str, dtype: type, lookback: int
) -> None:
    frame = _frame()
    before = np.geterr()
    expected = MomentumStrategy(lookback=lookback, skip=2).generate_signals(frame)
    with np.errstate(over=policy):
        actual = MomentumStrategy(lookback=dtype(lookback), skip=dtype(2)).generate_signals(frame)
    pd.testing.assert_series_equal(actual, expected)
    assert np.geterr() == before


@pytest.mark.parametrize("parameter", ["lookback", "skip"])
@pytest.mark.parametrize(
    "value",
    [
        True,
        np.bool_(True),
        5.0,
        np.float64(5),
        Fraction(5, 1),
        Fraction(3, 2),
        Decimal(5),
        float("nan"),
        float("inf"),
        "5",
        None,
        np.array(5),
        np.array([5]),
    ],
)
def test_momentum_constructor_rejects_original_nonintegral_counts(
    parameter: str, value: object
) -> None:
    with pytest.raises(ValueError, match=parameter):
        MomentumStrategy(**{parameter: value})


@pytest.mark.parametrize(
    "lookback,skip",
    [
        (1, 0),
        (np.int8(60), np.int8(5)),
        (np.int8(127), np.int8(2)),
        (np.uint8(255), np.uint8(2)),
        (np.uint64(2**64 - 1), np.uint64(2)),
        (10**100, 0),
    ],
)
def test_momentum_constructor_stores_exact_python_counts(lookback: int, skip: int) -> None:
    strategy = MomentumStrategy(lookback=lookback, skip=skip)
    assert type(strategy.lookback) is int
    assert type(strategy.skip) is int
    assert strategy.lookback + strategy.skip == int(lookback) + int(skip)
    assert strategy.parameters == {"lookback": int(lookback), "skip": int(skip)}


@pytest.mark.parametrize("parameter,value", [("lookback", 0), ("lookback", -1), ("skip", -1)])
def test_momentum_constructor_preserves_original_lower_bounds(parameter: str, value: int) -> None:
    with pytest.raises(ValueError, match=parameter):
        MomentumStrategy(**{parameter: value})


def test_momentum_nonwrapping_numpy_counts_and_zero_skip_preserve_signals() -> None:
    frame = _frame()
    for lookback, skip in [(1, 0), (60, 0), (60, 5)]:
        pd.testing.assert_series_equal(
            MomentumStrategy(np.int8(lookback), np.int8(skip)).generate_signals(frame),
            MomentumStrategy(lookback, skip).generate_signals(frame),
        )


@pytest.mark.parametrize("projection", ["signals", "returns"])
@settings(max_examples=20, deadline=None)
@given(
    lookback=st.integers(min_value=120, max_value=127), skip=st.integers(min_value=8, max_value=15)
)
def test_momentum_formerly_wrapping_counts_preserve_signal_and_net_return_prefixes(
    lookback: int, skip: int, projection: str
) -> None:
    frame = _frame()
    future = frame.copy()
    future.iloc[150:, 0] *= 0.8
    strategy = MomentumStrategy(np.int8(lookback), np.int8(skip))
    with np.errstate(over="ignore"):
        if projection == "signals":
            original = strategy.generate_signals(frame)
            altered = strategy.generate_signals(future)
        else:
            original = BacktestEngine().run_strategy(frame, strategy).returns
            altered = BacktestEngine().run_strategy(future, strategy).returns
    pd.testing.assert_series_equal(original.iloc[:150], altered.iloc[:150])
