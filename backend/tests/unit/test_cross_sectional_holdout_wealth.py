"""Holdout positive-wealth domain, preserving raw loss reporting (ADR-315)."""

from fractions import Fraction
from functools import reduce
from operator import mul

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional import search
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.registry import CrossSectionalStrategy, default_strategies


def _prices(short: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"LONG": [100.0] * len(short), "SHORT": short},
        index=pd.date_range("2020-01-01", periods=len(short), tz="UTC"),
    )


def _strategy() -> CrossSectionalStrategy:
    return default_strategies(value_scores={"LONG": 0.9, "SHORT": 0.1})["xs_value"]


@pytest.mark.parametrize("ratio", [2.0, 4.0])
def test_holdout_real_kernel_refuses_bankruptcy_and_negative_factor_recovery(ratio: float) -> None:
    prices = _prices([100.0, 100.0 * ratio, 100.0 * ratio**2])
    strategy = _strategy()
    raw = portfolio_returns(strategy.build({})(prices), prices, quantile=0.5, cost_rate=0.001)
    assert raw.tolist() == [-0.002, 1 - ratio, 1 - ratio]
    # Raw leveraged losses remain reportable; their product cannot certify scored wealth.
    with pytest.raises(ValueError, match="holdout returns must preserve positive wealth"):
        search._score_holdout(strategy, {}, 0.5, prices, prices.iloc[1:], 0.001)


@pytest.mark.parametrize("loss_at", [1, 2, 3])
def test_holdout_refuses_first_interior_last_insolvent_period(loss_at: int) -> None:
    prices = _prices([100.0 if i < loss_at else 400.0 for i in range(4)])
    with pytest.raises(ValueError, match="holdout returns must preserve positive wealth"):
        search._score_holdout(_strategy(), {}, 0.5, prices, prices.iloc[1:], 0.001)


def test_holdout_invalid_slice_refuses_before_benchmark_or_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prices = _prices([100.0, 400.0, 1600.0])

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("insolvent scored slice must refuse before benchmark or Sharpe")

    monkeypatch.setattr(search, "asset_returns", forbidden)
    monkeypatch.setattr(search, "sharpe_ratio", forbidden)
    with pytest.raises(ValueError, match="holdout returns must preserve positive wealth"):
        search._score_holdout(_strategy(), {}, 0.5, prices, prices.iloc[1:], 0.001)


@pytest.mark.parametrize("empty", [False, True])
def test_holdout_unsafe_warmup_outside_scored_slice_retains_original_result(empty: bool) -> None:
    prices = _prices([100.0, 400.0, 400.0, 400.0])
    holdout = prices.iloc[0:0] if empty else prices.iloc[2:]
    result = search._score_holdout(_strategy(), {}, 0.5, prices, holdout, 0.001)
    assert result.total_return == result.sharpe == result.buy_and_hold_sharpe == 0.0
    assert result.n_bars == len(holdout)


@pytest.mark.parametrize(
    "value,valid",
    [
        (Fraction(-1) - Fraction(1, 10**400), False),
        (Fraction(-1), False),
        (Fraction(-1) + Fraction(1, 10**400), True),
        (np.nextafter(np.longdouble(-1), np.longdouble(-2)), False),
        (np.longdouble(-1), False),
        (np.nextafter(np.longdouble(-1), np.longdouble(0)), True),
    ],
)
def test_holdout_inspects_original_native_return_before_float_product(
    monkeypatch: pytest.MonkeyPatch, value: object, valid: bool
) -> None:
    prices = _prices([100.0, 100.0, 100.0])
    dtype = np.dtype(np.longdouble) if isinstance(value, np.floating) else object
    returns = pd.Series([0, value, 0], index=prices.index, dtype=dtype)
    assert returns.iloc[1] == value
    # Isolate the consumer's native predicate, not a claim about actual kernel outputs.
    monkeypatch.setattr(search, "_config_returns", lambda *args: returns)
    monkeypatch.setattr(search, "sharpe_ratio", lambda *args: 0.0)
    if valid:
        result = search._score_holdout(_strategy(), {}, 0.5, prices, prices.iloc[1:], 0.001)
        assert result.n_bars == 2
        # An original positive gross factor can still round to zero in old aggregation.
        assert result.total_return >= -1.0
    else:
        with pytest.raises(ValueError, match="holdout returns must preserve positive wealth"):
            search._score_holdout(_strategy(), {}, 0.5, prices, prices.iloc[1:], 0.001)


@given(increments=st.lists(st.integers(-64, 64), min_size=2, max_size=12))
@settings(max_examples=30, deadline=None)
def test_holdout_solvent_returns_match_exact_fraction_wealth(increments: list[int]) -> None:
    prices = _prices([100.0] * len(increments))
    returns = pd.Series([v / 128 for v in increments], index=prices.index)
    exact_wealth = reduce(mul, (Fraction(128 + v, 128) for v in increments), Fraction(1))
    # No research source or search: test only the scored-return consumption boundary.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(search, "_config_returns", lambda *args: returns)
        result = search._score_holdout(_strategy(), {}, 0.5, prices, prices, 0.001)
    assert exact_wealth > 0
    assert result.total_return > -1
    assert result.total_return == pytest.approx(float(exact_wealth) - 1, rel=1e-12, abs=1e-12)
    assert result.n_bars == len(increments)
