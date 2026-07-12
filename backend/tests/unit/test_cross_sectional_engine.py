"""Cross-sectional portfolio engine (ADR-024). Realizes a portfolio return series from a signal
panel by holding each date's dollar-neutral weights to earn the NEXT bar's return (rank on t, trade
t+1 — the same `.shift(1)` the single-name BacktestEngine uses), net of turnover cost. The
load-bearing invariant — no look-ahead — is a Hypothesis truncation-invariance property test."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.engine import (
    asset_returns,
    portfolio_returns,
    split_panel_holdout,
)


def _prices(n_dates: int, n_symbols: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0005, 0.01, (n_dates, n_symbols))
    prices = 100.0 * np.cumprod(1.0 + steps, axis=0)
    idx = pd.date_range("2015-01-01", periods=n_dates, freq="B", tz="UTC")
    cols = [f"S{i}" for i in range(n_symbols)]
    return pd.DataFrame(prices, index=idx, columns=cols)


def test_asset_returns_are_pct_change_with_zero_first_bar() -> None:
    prices = _prices(5, 2, 0)
    rets = asset_returns(prices)
    assert (rets.iloc[0] == 0.0).all()
    pd.testing.assert_frame_equal(rets.iloc[1:], prices.pct_change().iloc[1:])


def test_portfolio_returns_earn_the_next_bar_return_of_the_held_legs() -> None:
    # A strictly rises, B strictly falls; long A / short B should earn a positive return.
    idx = pd.date_range("2020-01-01", periods=4, freq="B", tz="UTC")
    prices = pd.DataFrame({"A": [100, 101, 102, 103], "B": [100, 99, 98, 97]}, index=idx).astype(
        float
    )
    signals = pd.DataFrame({"A": [1.0] * 4, "B": [0.0] * 4}, index=idx)
    ret = portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.0)
    assert ret.iloc[2] > 0.0  # weights from t=1 earn the t=1->t=2 move (long winner, short loser)


def test_portfolio_returns_cost_reduces_total_return() -> None:
    prices = _prices(30, 4, 1)
    signals = prices.pct_change(5)  # a causal momentum-ish signal
    free = portfolio_returns(signals, prices, quantile=0.25, cost_rate=0.0).sum()
    costly = portfolio_returns(signals, prices, quantile=0.25, cost_rate=0.002).sum()
    assert costly < free  # turnover is charged, so costs always reduce returns


def test_portfolio_returns_rejects_negative_cost() -> None:
    prices = _prices(5, 2, 0)
    with pytest.raises(ValueError, match="cost_rate"):
        portfolio_returns(prices.pct_change(), prices, cost_rate=-0.001)


@settings(max_examples=40, deadline=None)
@given(
    n_dates=st.integers(min_value=6, max_value=40),
    n_symbols=st.integers(min_value=2, max_value=5),
    seed=st.integers(min_value=0, max_value=10_000),
    cut=st.floats(min_value=0.3, max_value=0.9),
)
def test_portfolio_returns_have_no_lookahead(
    n_dates: int, n_symbols: int, seed: int, cut: float
) -> None:
    # Truncation invariance: a portfolio return at date t depends only on prices <= t, so
    # recomputing on a panel truncated after date m reproduces the first m returns exactly. A
    # future price cannot change a past portfolio return.
    prices = _prices(n_dates, n_symbols, seed)
    signals = prices.pct_change(3)  # causal signal built from the same prices
    m = max(2, int(cut * n_dates))
    full = portfolio_returns(signals, prices, quantile=0.4, cost_rate=0.001)
    truncated = portfolio_returns(signals.iloc[:m], prices.iloc[:m], quantile=0.4, cost_rate=0.001)
    pd.testing.assert_series_equal(full.iloc[:m], truncated, check_exact=False, atol=1e-12)


def test_split_panel_holdout_takes_the_calendar_latest_tail() -> None:
    prices = _prices(1500, 3, 2)
    in_sample, holdout = split_panel_holdout(prices)
    assert len(holdout) == 300 and len(in_sample) == 1200  # max(0.2*1500, 252) = 300
    assert in_sample.index.max() < holdout.index.min()  # holdout is strictly later
    assert list(in_sample.columns) == list(prices.columns)


def test_split_panel_holdout_raises_when_search_head_too_short() -> None:
    prices = _prices(300, 3, 3)  # holdout 252 -> only 48 search bars
    with pytest.raises(ValueError, match="insufficient data"):
        split_panel_holdout(prices)


def test_split_panel_holdout_rejects_bad_fraction() -> None:
    prices = _prices(1500, 3, 4)
    with pytest.raises(ValueError, match="holdout_fraction"):
        split_panel_holdout(prices, holdout_fraction=1.5)
