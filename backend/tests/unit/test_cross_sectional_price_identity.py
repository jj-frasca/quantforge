"""Price column identity cannot duplicate a ranked portfolio leg (ADR-263)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.engine import asset_returns, portfolio_returns


@pytest.mark.parametrize("rows", [0, 1, 3])
@pytest.mark.parametrize(
    "labels", [["A", "A", "B"], [1, 1, 2], [np.nan, np.nan, "B"], [("A", 1), ("A", 1), ("B", 2)]]
)
def test_asset_returns_refuses_duplicate_original_price_columns(
    rows: int, labels: list[object]
) -> None:
    prices = pd.DataFrame(np.full((rows, len(labels)), 100.0), columns=labels)
    before = prices.copy(deep=True)
    assert not prices.columns.is_unique
    with pytest.raises(ValueError, match="price columns must be unique"):
        asset_returns(prices)
    pd.testing.assert_frame_equal(prices, before, check_exact=True)


def test_asset_returns_refuses_duplicate_price_identity_before_numeric_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_pct_change(*_: object, **__: object) -> None:
        pytest.fail("duplicate identity must not reach price arithmetic")

    monkeypatch.setattr(pd.DataFrame, "pct_change", forbid_pct_change)
    prices = pd.DataFrame([["bad", "bad"]], columns=["A", "A"])
    with pytest.raises(ValueError, match="price columns must be unique"):
        asset_returns(prices)


def test_asset_returns_retains_calendar_refusal_before_duplicate_columns() -> None:
    prices = pd.DataFrame([[100.0, 100.0], [110.0, 110.0]], columns=["A", "A"], index=[1, 0])
    with pytest.raises(ValueError, match="index must be unique and ascending"):
        asset_returns(prices)


@pytest.mark.parametrize("flat", [False, True])
def test_portfolio_returns_refuses_duplicate_prices_that_repeat_a_ranked_leg(flat: bool) -> None:
    signals = pd.DataFrame({"A": [np.nan if flat else 1.0] * 2, "B": [np.nan if flat else 2.0] * 2})
    prices = pd.DataFrame([[100.0, 100.0, 100.0], [110.0, 110.0, 100.0]], columns=["A", "A", "B"])
    before = signals.copy(deep=True), prices.copy(deep=True)
    with pytest.raises(ValueError, match="price columns must be unique"):
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)
    pd.testing.assert_frame_equal(signals, before[0], check_exact=True)
    pd.testing.assert_frame_equal(prices, before[1], check_exact=True)


@pytest.mark.parametrize("cost", [-1.0, np.nan, np.inf])
def test_portfolio_returns_retains_cost_precedence_for_duplicate_prices(cost: float) -> None:
    signals = pd.DataFrame({"A": [1.0]})
    prices = pd.DataFrame([[100.0, 100.0]], columns=["A", "A"])
    with pytest.raises(ValueError, match="cost_rate"):
        portfolio_returns(signals, prices, cost_rate=cost)


def test_portfolio_returns_retains_unpriced_signal_precedence_for_duplicate_prices() -> None:
    signals = pd.DataFrame({"X": [1.0]})
    prices = pd.DataFrame([[100.0, 100.0]], columns=["A", "A"])
    with pytest.raises(ValueError, match="signal names must have price columns"):
        portfolio_returns(signals, prices)


@pytest.mark.parametrize("labels", [["A", "B"], [2, 1], [np.nan, "B"], [("A", 1), ("B", 2)]])
def test_asset_returns_preserves_unique_original_column_labels_and_order(
    labels: list[object],
) -> None:
    prices = pd.DataFrame([[100.0, 100.0], [110.0, 100.0]], columns=labels)
    actual = asset_returns(prices)
    pd.testing.assert_index_equal(actual.columns, prices.columns, exact=True)
    np.testing.assert_allclose(actual, [[0.0, 0.0], [0.1, 0.0]], rtol=1e-14, atol=0)


@pytest.mark.parametrize("empty", ["rows", "columns"])
def test_asset_returns_preserves_unique_empty_panels(empty: str) -> None:
    prices = pd.DataFrame(np.ones((2, 2)), columns=["A", "B"])
    prices = prices.iloc[:0] if empty == "rows" else prices.iloc[:, :0]
    actual = asset_returns(prices)
    pd.testing.assert_frame_equal(actual, prices, check_exact=True)


def test_portfolio_returns_preserves_unique_price_leg_accounting() -> None:
    signals = pd.DataFrame({"A": [1.0, 1.0], "B": [2.0, 2.0]})
    prices = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 100.0]})
    np.testing.assert_allclose(
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001),
        [-0.002, -0.1],
        rtol=1e-14,
        atol=0,
    )


@given(
    rows=st.integers(0, 8),
    symbols=st.integers(2, 7),
    duplicate=st.integers(0, 6),
    flat=st.booleans(),
)
def test_portfolio_returns_never_publishes_a_duplicated_price_leg(
    rows: int, symbols: int, duplicate: int, flat: bool
) -> None:
    names = [f"S{i}" for i in range(symbols)]
    signals = pd.DataFrame(
        np.full((rows, symbols), np.nan) if flat else np.tile(np.arange(symbols), (rows, 1)),
        columns=names,
    )
    prices = pd.DataFrame(
        np.full((rows, symbols + 1), 100.0), columns=[*names, names[duplicate % symbols]]
    )
    with pytest.raises(ValueError, match="price columns must be unique"):
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001)


@pytest.mark.parametrize("duplicate", [False, True])
def test_asset_returns_preserves_unique_multiindex_and_refuses_duplicate_multiindex(
    duplicate: bool,
) -> None:
    columns = pd.MultiIndex.from_tuples([("A", "close"), ("A" if duplicate else "B", "close")])
    prices = pd.DataFrame([[100.0, 100.0], [110.0, 100.0]], columns=columns)
    if duplicate:
        with pytest.raises(ValueError, match="price columns must be unique"):
            asset_returns(prices)
    else:
        actual = asset_returns(prices)
        pd.testing.assert_index_equal(actual.columns, columns, exact=True)
        np.testing.assert_allclose(actual, [[0.0, 0.0], [0.1, 0.0]], rtol=1e-14, atol=0)
