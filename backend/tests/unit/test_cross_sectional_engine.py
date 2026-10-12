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


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 0.0, -1.0])
@pytest.mark.parametrize("location", ["first", "interior", "last", "singleton"])
def test_asset_returns_refuses_invalid_original_price(bad: float, location: str) -> None:
    values = [100.0] if location == "singleton" else [100.0, 101.0, 102.0]
    index = {"first": 0, "interior": 1, "last": 2, "singleton": 0}[location]
    values[index] = bad
    with pytest.raises(ValueError):
        asset_returns(pd.DataFrame({"A": values, "B": [100.0] * len(values)}))


@pytest.mark.parametrize("values", [[True, False], ["100", "101"], [100 + 1j, 101 + 1j]])
def test_asset_returns_refuses_nonreal_original_price_dtype(values: list[object]) -> None:
    with pytest.raises(ValueError):
        asset_returns(pd.DataFrame({"A": values}))


def test_asset_returns_refuses_object_numeric_prices_without_coercion() -> None:
    prices = pd.DataFrame({"A": pd.Series([100.0, 101.0], dtype=object)})
    with pytest.raises(ValueError):
        asset_returns(prices)


@pytest.mark.parametrize("zero_exposure", [False, True])
def test_portfolio_returns_refuses_missing_prices_even_without_exposure(
    zero_exposure: bool,
) -> None:
    prices = pd.DataFrame({"A": [100.0, np.nan, 110.0], "B": [100.0] * 3})
    signals = pd.DataFrame({"A": [1.0] * 3, "B": [-1.0] * 3})
    if zero_exposure:
        signals[:] = np.nan
    with pytest.raises(ValueError):
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)


@pytest.mark.parametrize(
    "kind", ["float64", "Float64", "Int64", "uint64", "longdouble", "empty", "zero_columns"]
)
def test_asset_returns_preserves_native_complete_and_zero_cell_panels(kind: str) -> None:
    if kind == "empty":
        prices = pd.DataFrame(columns=["A", "B"])
    elif kind == "zero_columns":
        prices = pd.DataFrame(index=[0, 1])
    elif kind == "uint64":
        prices = pd.DataFrame({"A": np.array([2**64 - 3, 2**64 - 2, 2**64 - 1], dtype=np.uint64)})
    elif kind == "longdouble":
        values = np.array(["1e400", "2e400", "3e400"], dtype=np.longdouble)
        if not np.isfinite(values).all():
            values = np.array([100, 101, 102], dtype=np.longdouble)
        prices = pd.DataFrame({"A": values})
    else:
        prices = pd.DataFrame({"A": pd.Series([100, 101, 102], dtype=kind)})
    original = prices.copy(deep=True)
    expected = prices.pct_change().fillna(0.0)
    pd.testing.assert_frame_equal(asset_returns(prices), expected)
    pd.testing.assert_frame_equal(prices, original)


@given(
    values=st.lists(
        st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=20,
    ),
    scale=st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False),
)
def test_asset_returns_are_invariant_to_positive_price_scale(
    values: list[float], scale: float
) -> None:
    prices = pd.DataFrame({"A": values, "B": values[::-1]})
    pd.testing.assert_frame_equal(
        asset_returns(prices), asset_returns(prices * scale), rtol=1e-12, atol=1e-12
    )


@pytest.mark.parametrize("mutation", ["reverse", "shuffle", "duplicate"])
def test_asset_returns_refuses_noncausal_source_calendar(mutation: str) -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0, 120.0], "B": [100.0] * 3})
    prices.index = {"reverse": [2, 1, 0], "shuffle": [0, 2, 1], "duplicate": [0, 0, 1]}[mutation]
    with pytest.raises(ValueError):
        asset_returns(prices)


@pytest.mark.parametrize("mutation", ["reverse", "shuffle", "duplicate"])
@pytest.mark.parametrize("zero_exposure", [False, True])
def test_portfolio_returns_refuses_noncausal_calendar_without_repair(
    mutation: str, zero_exposure: bool
) -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0, 120.0], "B": [100.0] * 3})
    prices.index = {"reverse": [2, 1, 0], "shuffle": [0, 2, 1], "duplicate": [0, 0, 1]}[mutation]
    signals = pd.DataFrame({"A": [1.0] * 3, "B": [-1.0] * 3}, index=prices.index)
    if zero_exposure:
        signals[:] = np.nan
    with pytest.raises(ValueError):
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)


def test_asset_calendar_refusal_precedes_pct_change(monkeypatch: pytest.MonkeyPatch) -> None:
    prices = pd.DataFrame({"A": [100.0, 101.0]}, index=[1, 0])

    def unexpected_returns(*_: object, **__: object) -> None:
        pytest.fail("noncausal source cannot reach return computation")

    monkeypatch.setattr(pd.DataFrame, "pct_change", unexpected_returns)
    with pytest.raises(ValueError):
        asset_returns(prices)


@pytest.mark.parametrize(
    "calendar", ["integers", "strings", "naive", "aware", "empty", "singleton"]
)
def test_asset_returns_preserves_ordered_native_calendar_and_caller(calendar: str) -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0, 120.0], "B": [100.0, 99.0, 98.0]})
    if calendar == "strings":
        prices.index = ["a", "b", "c"]
    elif calendar == "naive":
        prices.index = pd.date_range("2020-01-01", periods=3)
    elif calendar == "aware":
        prices.index = pd.date_range("2020-01-01", periods=3, tz="UTC")
    elif calendar == "empty":
        prices = prices.iloc[:0]
    elif calendar == "singleton":
        prices = prices.iloc[:1]
    original = prices.copy(deep=True)
    pd.testing.assert_frame_equal(asset_returns(prices), prices.pct_change().fillna(0.0))
    pd.testing.assert_frame_equal(prices, original)


@given(order=st.permutations((0, 1, 2)).filter(lambda order: tuple(order) != (0, 1, 2)))
def test_asset_returns_refuses_every_nonidentity_source_permutation(order: list[int]) -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0, 120.0], "B": [100.0] * 3})
    with pytest.raises(ValueError):
        asset_returns(prices.iloc[list(order)])


@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_asset_returns_refuses_native_ratio_overflow(error_mode: str) -> None:
    prices = pd.DataFrame({"A": [np.finfo(float).tiny, np.finfo(float).max], "B": [100.0] * 2})
    with np.errstate(all=error_mode):
        before = np.geterr()
        with pytest.raises(ValueError):
            asset_returns(prices)
        assert np.geterr() == before


@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("zero_exposure", [False, True])
def test_portfolio_returns_refuses_asset_overflow_instead_of_flat_output(
    error_mode: str, zero_exposure: bool
) -> None:
    prices = pd.DataFrame({"A": [np.finfo(float).tiny, np.finfo(float).max], "B": [100.0] * 2})
    signals = pd.DataFrame({"A": [1.0] * 2, "B": [-1.0] * 2})
    if zero_exposure:
        signals[:] = np.nan
    with np.errstate(all=error_mode):
        before = np.geterr()
        with pytest.raises(ValueError):
            portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)
        assert np.geterr() == before


@pytest.mark.parametrize("error", [OverflowError, FloatingPointError])
def test_asset_returns_normalizes_native_arithmetic_overflow(
    error: type[ArithmeticError], monkeypatch: pytest.MonkeyPatch
) -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0]})

    def fail_native(*_: object, **__: object) -> None:
        raise error("synthetic native overflow")

    monkeypatch.setattr(pd.DataFrame, "pct_change", fail_native)
    with pytest.raises(ValueError):
        asset_returns(prices)


@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_asset_returns_preserves_representable_extreme_ratios_and_error_state(
    error_mode: str,
) -> None:
    prices = pd.DataFrame({"A": [1e-150, 1e150], "B": [1e150, 1e-150]})
    original = prices.copy(deep=True)
    with np.errstate(all=error_mode):
        before = np.geterr()
        expected = prices.pct_change().fillna(0.0)
        pd.testing.assert_frame_equal(asset_returns(prices), expected)
        assert np.geterr() == before
    pd.testing.assert_frame_equal(prices, original)


@given(small_exponent=st.integers(100, 200), large_exponent=st.integers(210, 300))
def test_asset_returns_refuses_constructed_unrepresentable_ratios(
    small_exponent: int, large_exponent: int
) -> None:
    prices = pd.DataFrame({"A": [10.0**-small_exponent, 10.0**large_exponent]})
    with pytest.raises(ValueError):
        asset_returns(prices)
