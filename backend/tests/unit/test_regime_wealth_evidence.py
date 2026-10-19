"""ADR-320: matched regime factors cannot revive bankrupt or negative wealth."""

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.backtesting.metrics import sharpe_ratio
from app.validation.regime_analysis import analyze_regimes


@pytest.mark.parametrize("bad", [-1.0, -2.0, -3.0])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_every_matched_insolvent_period_refuses_before_market_scoring(
    bad: float, position: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = [0.01, -0.02, 0.03]
    values[position] = bad
    returns, market = pd.Series(values), pd.Series([100.0, 101.0, 99.0])

    def forbidden_market_calculation(*args: object, **kwargs: object) -> None:
        pytest.fail("insolvent matched return reached market/scoring work")

    monkeypatch.setattr(pd.Series, "pct_change", forbidden_market_calculation)
    with pytest.raises(ValueError, match="above -1"):
        analyze_regimes(returns, market, window=1)


@pytest.mark.parametrize("values", [[-3.0, -3.0], [-2.0, -3.0], [-1.0, 0.02]])
def test_real_public_compounding_revival_and_bankruptcy_refuse(values: list[float]) -> None:
    with pytest.raises(ValueError, match="above -1"):
        analyze_regimes(pd.Series(values), pd.Series([100.0] * len(values)), window=1)


@pytest.mark.parametrize("bad", [-1.0, -2.0, -3.0])
def test_unsafe_return_outside_intersection_remains_unscored(bad: float) -> None:
    returns = pd.Series([bad, 0.01, -0.02], index=[0, 1, 2])
    market = pd.Series([100.0, 100.0], index=[1, 2])
    result = analyze_regimes(returns, market, window=1)
    assert set(result) == {"bull"}
    assert result["bull"].n_bars == 2
    assert result["bull"].total_return == (1.01 * 0.98) - 1
    assert result["bull"].sharpe == sharpe_ratio(returns.loc[[1, 2]])


def test_empty_and_disjoint_unsafe_returns_retain_empty_results() -> None:
    empty = pd.Series([], dtype=float)
    assert analyze_regimes(empty, empty) == {}
    returns = pd.Series([-3.0, -3.0], index=[0, 1])
    market = pd.Series([100.0, 100.0], index=[2, 3])
    assert analyze_regimes(returns, market, window=1) == {}


@pytest.mark.parametrize("dtype", [np.float64, np.longdouble])
def test_native_value_immediately_above_bankruptcy_retains_scoring(dtype: type) -> None:
    value = np.nextafter(dtype(-1), dtype(0))
    returns = pd.Series(np.array([value, dtype(0)], dtype=dtype), dtype=dtype)
    assert returns.iloc[0] == value and returns.iloc[0] > -1
    before = returns.copy(deep=True)
    result = analyze_regimes(returns, pd.Series([100.0, 100.0]), window=1)
    assert result["bull"].n_bars == 2
    assert math.isfinite(result["bull"].total_return)
    pd.testing.assert_series_equal(returns, before)


@pytest.mark.parametrize("dtype", [np.float64, np.longdouble])
def test_native_value_immediately_below_bankruptcy_refuses(dtype: type) -> None:
    value = np.nextafter(dtype(-1), dtype(-2))
    returns = pd.Series(np.array([value, dtype(0)], dtype=dtype), dtype=dtype)
    assert returns.iloc[0] == value and returns.iloc[0] < -1
    with pytest.raises(ValueError, match="above -1"):
        analyze_regimes(returns, pd.Series([100.0, 100.0]), window=1)


def test_original_window_and_calendar_checks_precede_wealth_guard() -> None:
    returns = pd.Series([-3.0, -3.0], index=[1, 0])
    market = pd.Series([100.0, 100.0], index=[1, 0])
    with pytest.raises(ValueError, match="window"):
        analyze_regimes(returns, market, window=-1)
    with pytest.raises(ValueError, match=r"unique.*ascending"):
        analyze_regimes(returns, market, window=1)


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_insolvent_refusal_does_not_change_numpy_error_policy(policy: str) -> None:
    with np.errstate(all=policy):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="above -1"):
            analyze_regimes(pd.Series([-3.0, -3.0]), pd.Series([100.0, 100.0]), window=0)
        assert np.geterr() == before


@given(
    values=st.lists(
        st.floats(-0.5, 0.5, allow_nan=False, allow_infinity=False), min_size=2, max_size=30
    ),
    bad=st.floats(-10, -1, allow_nan=False, allow_infinity=False),
    position_seed=st.integers(0, 100),
    window=st.integers(0, 10),
)
def test_any_matched_insolvent_factor_refuses_without_source_mutation(
    values: list[float], bad: float, position_seed: int, window: int
) -> None:
    values[position_seed % len(values)] = bad
    returns, market = pd.Series(values), pd.Series([100.0] * len(values))
    before = returns.copy(deep=True)
    with pytest.raises(ValueError, match="above -1"):
        analyze_regimes(returns, market, window=window)
    pd.testing.assert_series_equal(returns, before)


@given(
    losses=st.lists(
        st.floats(-0.99, 0, allow_nan=False, allow_infinity=False), min_size=2, max_size=30
    )
)
def test_solvent_nonpositive_factors_cannot_manufacture_positive_regime_return(
    losses: list[float],
) -> None:
    returns, market = pd.Series(losses), pd.Series([100.0] * len(losses))
    result = analyze_regimes(returns, market, window=0)["bull"]
    assert result.n_bars == len(losses)
    assert -1.0 <= result.total_return <= 0.0
    assert math.isfinite(result.sharpe)
