"""ADR-343: infinity is invalid aligned weight evidence; warmup remains flat."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.engine import BacktestEngine


@pytest.mark.parametrize("dtype", ["float32", "float64", np.longdouble, "Float64"])
@pytest.mark.parametrize("value", [np.inf, -np.inf])
@pytest.mark.parametrize("n_rows,row", [(3, 0), (3, 1), (3, 2), (1, 0)])
def test_backtest_rejects_infinity_at_every_aligned_observation(
    dtype: object, value: float, n_rows: int, row: int
) -> None:
    prices = pd.Series([100.0] * n_rows)
    values = [0.0] * n_rows
    values[row] = value
    signals = pd.Series(values, dtype=dtype)
    assert np.isinf(signals.iloc[row])
    with pytest.raises(ValueError, match=r"signals.*infinity"):
        BacktestEngine(cost_rate=0).run(prices, signals)


@pytest.mark.parametrize("dtype", ["float32", "float64", np.longdouble, "Float64"])
def test_backtest_preserves_missing_warmup_and_finite_clipping(dtype: object) -> None:
    prices = pd.Series([100.0, 110.0, 121.0])
    signals = pd.Series([np.nan, 2.0, -2.0], dtype=dtype)
    out = BacktestEngine().run(prices, signals)
    np.testing.assert_array_equal(out.position.to_numpy(dtype=float), [0.0, 1.0, -1.0])
    assert np.isfinite(out.returns.to_numpy(dtype=float)).all()
    assert np.isfinite(out.equity_curve.to_numpy(dtype=float)).all()


def test_backtest_preserves_original_native_wide_finite_weights() -> None:
    weights = np.array([np.finfo(np.longdouble).max, 0.0, -0.0], dtype=np.longdouble)
    assert np.isfinite(weights).all()
    signals = pd.Series(weights, dtype=np.longdouble)
    assert signals.dtype == np.dtype(np.longdouble)
    out = BacktestEngine().run(pd.Series([100.0, 110.0, 121.0]), signals)
    np.testing.assert_array_equal(out.position.to_numpy(), [1.0, 0.0, -0.0])
    assert out.position.dtype == signals.dtype


def test_backtest_ignores_unmatched_infinity_during_sparse_alignment() -> None:
    prices = pd.Series([100.0, 110.0, 121.0])
    original = pd.Series([0.5, np.inf, -np.inf], index=[0, 99, 100])
    expected = BacktestEngine().run(prices, original.iloc[:1])
    actual = BacktestEngine().run(prices, original)
    pd.testing.assert_series_equal(actual.position, expected.position, check_exact=True)
    pd.testing.assert_series_equal(actual.returns, expected.returns, check_exact=True)
    pd.testing.assert_series_equal(actual.equity_curve, expected.equity_curve, check_exact=True)
    assert actual.metrics == expected.metrics
    assert actual.n_trades == expected.n_trades


def test_backtest_preserves_empty_prices_with_unmatched_infinity() -> None:
    out = BacktestEngine().run(pd.Series([], dtype=float), pd.Series([np.inf]))
    assert out.position.empty and out.returns.empty and out.equity_curve.empty
    assert out.metrics.total_return == 0 and out.n_trades == 0


@pytest.mark.parametrize(
    "prices,match",
    [(pd.Series([0.0]), "prices"), (pd.Series([100.0, 110.0], index=[1, 0]), "calendar")],
)
def test_backtest_preserves_price_error_precedence_with_infinite_signals(
    prices: pd.Series, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        BacktestEngine().run(prices, pd.Series(np.inf, index=prices.index))


@given(
    weights=st.lists(
        st.floats(-4, 4, allow_nan=False, allow_infinity=False), min_size=1, max_size=20
    ),
    value=st.sampled_from([np.inf, -np.inf]),
    offset=st.integers(0, 100),
)
@settings(max_examples=30)
def test_backtest_never_publishes_performance_from_aligned_infinity(
    weights: list[float], value: float, offset: int
) -> None:
    signals = pd.Series(weights)
    signals.iloc[offset % len(weights)] = value
    with pytest.raises(ValueError, match=r"signals.*infinity"):
        BacktestEngine().run(pd.Series([100.0] * len(weights)), signals)


@given(
    weights=st.lists(
        st.floats(-4, 4, allow_nan=False, allow_infinity=False), min_size=1, max_size=20
    )
)
@settings(max_examples=30)
def test_backtest_finite_saturation_is_equivalent_to_bounded_weights(weights: list[float]) -> None:
    prices = pd.Series([100.0] * len(weights))
    raw = pd.Series(weights)
    bounded = pd.Series([max(-1.0, min(1.0, weight)) for weight in weights])
    actual = BacktestEngine().run(prices, raw)
    expected = BacktestEngine().run(prices, bounded)
    pd.testing.assert_series_equal(actual.position, expected.position, check_exact=True)
    pd.testing.assert_series_equal(actual.returns, expected.returns, check_exact=True)
    pd.testing.assert_series_equal(actual.equity_curve, expected.equity_curve, check_exact=True)
    assert actual.metrics == expected.metrics
