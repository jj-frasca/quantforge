"""BacktestEngine + metrics: the §8 oracle tests (buy-and-hold matches the analytic closed form, zero signal flat, long/short symmetry, monotonic cost impact) plus drawdown bounds and the Hypothesis invariant that long-only equity stays finite and positive."""

from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from scipy.stats import norm
from tests.fixtures.synthetic import builders

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import (
    TRADING_DAYS,
    BacktestMetrics,
    annualized_return,
    calmar_ratio,
    max_drawdown,
    sharpe_confidence_interval,
    sharpe_ratio,
    sortino_ratio,
    total_return,
)
from app.research.frames import bars_to_frame
from app.research.strategies.sma import SMAStrategy


def _prices(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=index, dtype="float64")


def _trend(n: int = 50, start: float = 100.0, step: float = 0.001) -> pd.Series:
    return _prices([start * (1 + step) ** i for i in range(n)])


# --- §8 oracle tests ---


def test_buy_and_hold_matches_analytic_closed_form() -> None:
    prices = _trend(60)
    signals = pd.Series(1.0, index=prices.index)
    result = BacktestEngine(initial_capital=100_000.0, cost_rate=0.0).run(prices, signals)
    expected = 100_000.0 * prices / prices.iloc[0]
    assert np.allclose(result.equity_curve.to_numpy(), expected.to_numpy(), rtol=1e-9, atol=1e-6)


def test_zero_signal_produces_zero_exposure() -> None:
    prices = _trend(40)
    signals = pd.Series(0.0, index=prices.index)
    result = BacktestEngine(cost_rate=0.001).run(prices, signals)
    assert result.n_trades == 0
    assert result.metrics.total_return == pytest.approx(0.0)
    assert result.metrics.sharpe == 0.0
    assert np.allclose(result.equity_curve.to_numpy(), result.equity_curve.iloc[0])


def test_symmetric_long_short_nets_near_zero_without_costs() -> None:
    prices = _trend(60)
    signals = pd.Series(
        [1.0 if i % 2 == 0 else -1.0 for i in range(len(prices))], index=prices.index
    )
    result = BacktestEngine(cost_rate=0.0).run(prices, signals)
    assert abs(result.metrics.total_return) < 0.01


def test_transaction_cost_reduces_returns_monotonically() -> None:
    prices = _trend(60)
    signals = pd.Series(
        [1.0 if i % 2 == 0 else -1.0 for i in range(len(prices))], index=prices.index
    )
    returns = [
        BacktestEngine(cost_rate=c).run(prices, signals).metrics.total_return
        for c in (0.0, 0.001, 0.005, 0.01)
    ]
    for earlier, later in pairwise(returns):
        assert earlier >= later


def test_max_drawdown_is_in_unit_interval() -> None:
    prices = _prices([100, 90, 80, 120, 60, 130])
    signals = pd.Series(1.0, index=prices.index)
    result = BacktestEngine(cost_rate=0.0).run(prices, signals)
    assert -1.0 <= result.metrics.max_drawdown <= 0.0


def test_engine_rejects_bad_config() -> None:
    with pytest.raises(ValueError, match="capital"):
        BacktestEngine(initial_capital=0.0)
    with pytest.raises(ValueError, match="cost"):
        BacktestEngine(cost_rate=-0.1)


def test_run_strategy_executes_sma_end_to_end() -> None:
    frame = bars_to_frame(builders.clean_series(n=40))
    result = BacktestEngine(cost_rate=0.001).run_strategy(frame, SMAStrategy(fast=5, slow=10))
    assert len(result.equity_curve) == 40
    assert result.equity_curve.iloc[0] == pytest.approx(100_000.0)


def test_metrics_handle_empty_series() -> None:
    empty = pd.Series(dtype="float64")
    assert sharpe_ratio(empty) == 0.0
    assert max_drawdown(empty) == 0.0
    assert total_return(empty) == 0.0
    assert sortino_ratio(empty) == 0.0
    metrics = BacktestMetrics.from_series(empty)
    assert metrics.total_return == 0.0
    assert metrics.annualized_return == 0.0
    assert metrics.max_drawdown == 0.0


def test_sortino_ratio_zero_for_single_observation() -> None:
    assert sortino_ratio(pd.Series([0.01])) == 0.0


def test_sortino_ratio_zero_when_no_return_falls_below_target() -> None:
    # Every return is >= target (0.0 by default): downside deviation is 0, so ADR-107's
    # convention returns 0.0 rather than +inf (mirrors sharpe_ratio's degenerate case).
    assert sortino_ratio(pd.Series([0.0, 0.01, 0.02, 0.0])) == 0.0


def test_sortino_ratio_downside_deviation_ignores_upside_dispersion() -> None:
    # Two series with identical downside returns but very different upside swings must have the
    # same downside semi-deviation — only shortfall below target enters it (ADR-107). Replicates
    # the public formula (same one test_sortino_ratio_matches_hand_computed_value checks) rather
    # than asserting on the full ratio, whose numerator DOES move with the upside mean.
    target = 0.0

    def semi_std(returns: pd.Series) -> float:
        shortfall = np.minimum(returns.to_numpy() - target, 0.0)
        return float(np.sqrt(np.mean(shortfall**2)))

    steady_upside = pd.Series([-0.01, 0.01, -0.02, 0.01, -0.01, 0.01])
    volatile_upside = pd.Series([-0.01, 0.10, -0.02, 0.15, -0.01, 0.20])
    assert semi_std(steady_upside) == pytest.approx(semi_std(volatile_upside))


def test_sortino_ratio_matches_hand_computed_value() -> None:
    returns = pd.Series([0.02, -0.01, 0.03, -0.02, 0.01])
    target = 0.0
    shortfall = np.minimum(returns.to_numpy() - target, 0.0)
    semi_std = float(np.sqrt(np.mean(shortfall**2)))
    expected = float(np.sqrt(252) * (returns.mean() - target) / semi_std)
    assert sortino_ratio(returns) == pytest.approx(expected)


def test_calmar_ratio_zero_when_max_drawdown_is_zero() -> None:
    # ADR-108: a flat/never-drawn-down equity curve returns 0.0, not +inf — mirrors
    # sharpe_ratio's and sortino_ratio's degenerate-series convention.
    assert calmar_ratio(annualized_return=0.12, max_drawdown=0.0) == 0.0


def test_calmar_ratio_divides_annualized_return_by_drawdown_magnitude() -> None:
    assert calmar_ratio(annualized_return=0.20, max_drawdown=-0.10) == pytest.approx(2.0)


def test_calmar_ratio_is_negative_for_a_losing_strategy() -> None:
    assert calmar_ratio(annualized_return=-0.05, max_drawdown=-0.10) == pytest.approx(-0.5)


def test_return_metrics_include_initial_turnover_cost() -> None:
    prices = _prices([100.0, 100.0])
    signals = pd.Series(1.0, index=prices.index)

    metrics = BacktestEngine(cost_rate=0.10).run(prices, signals).metrics

    assert metrics.total_return == pytest.approx(-0.10)
    assert metrics.annualized_return < 0.0
    assert metrics.calmar < 0.0


def test_annualized_return_and_calmar_follow_compounded_wealth() -> None:
    # Positive arithmetic mean (+1% per period) but negative compounded wealth:
    # 1.20 * 0.82 = 0.984 for every pair. Arithmetic mean annualization reverses the sign.
    returns = pd.Series([0.20, -0.18] * 126, dtype="float64")

    metrics = BacktestMetrics.from_series(returns)
    expected_total = float((1.0 + returns).prod() - 1.0)
    expected_annualized = float((1.0 + expected_total) ** (TRADING_DAYS / len(returns)) - 1.0)

    assert metrics.total_return == pytest.approx(expected_total)
    assert metrics.annualized_return == pytest.approx(expected_annualized)
    assert metrics.total_return < 0.0
    assert metrics.annualized_return < 0.0
    assert metrics.calmar < 0.0


@pytest.mark.parametrize("invalid_return", [np.nan, np.inf, -np.inf, -1.0])
def test_return_metrics_reject_invalid_compounded_wealth(invalid_return: float) -> None:
    with pytest.raises(ValueError, match=r"returns|wealth"):
        BacktestMetrics.from_series(pd.Series([0.0, invalid_return]))


def test_return_metrics_reject_compounded_wealth_underflow() -> None:
    with pytest.raises(ValueError, match="wealth"):
        BacktestMetrics.from_series(pd.Series([-0.90] * 400))


def test_total_return_rejects_compounded_wealth_overflow() -> None:
    with pytest.raises(ValueError, match="wealth"):
        total_return(pd.Series([1e308, 1e308]))


def test_annualized_return_rejects_annual_wealth_overflow() -> None:
    with pytest.raises(ValueError, match="wealth"):
        annualized_return(pd.Series([1e308, 0.0]))


def test_return_metrics_reject_intermediate_wealth_overflow() -> None:
    # Terminal log wealth is finite after the losses, but the path overflows at its second peak.
    returns = pd.Series([1e308, 1e308] + [-0.999999999999999] * 40)
    with pytest.raises(ValueError, match="wealth path"):
        BacktestMetrics.from_series(returns)


def test_sharpe_confidence_interval_none_below_two_returns() -> None:
    assert sharpe_confidence_interval(pd.Series([0.01])) is None


def test_sharpe_confidence_interval_none_below_one_year_of_data() -> None:
    # ADR-109: the asymptotic Lo (2002) approximation is unreliable below a year of data.
    short = pd.Series(np.full(TRADING_DAYS - 1, 0.001))
    assert sharpe_confidence_interval(short) is None


def test_sharpe_confidence_interval_present_at_one_year_of_data() -> None:
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.0005, 0.01, TRADING_DAYS))
    ci = sharpe_confidence_interval(returns)
    assert ci is not None
    assert ci.confidence == pytest.approx(0.95)


def test_sharpe_confidence_interval_brackets_the_point_estimate() -> None:
    rng = np.random.default_rng(11)
    returns = pd.Series(rng.normal(0.0003, 0.012, 3 * TRADING_DAYS))
    point = sharpe_ratio(returns)
    ci = sharpe_confidence_interval(returns)
    assert ci is not None
    assert ci.lower <= point <= ci.upper


def test_sharpe_confidence_interval_matches_hand_computed_bounds() -> None:
    rng = np.random.default_rng(13)
    returns = pd.Series(rng.normal(0.0004, 0.011, 2 * TRADING_DAYS))
    point = sharpe_ratio(returns)
    years = len(returns) / TRADING_DAYS
    se = np.sqrt((1.0 + point**2 / (2.0 * TRADING_DAYS)) / years)
    z = norm.ppf(0.975)
    ci = sharpe_confidence_interval(returns)
    assert ci is not None
    assert ci.lower == pytest.approx(point - z * se)
    assert ci.upper == pytest.approx(point + z * se)


# --- Hypothesis invariants ---


@settings(deadline=None)
@given(
    # realistic bounded daily returns (the quality gate flags >20% moves); a price path
    # built from these keeps long-only net > -1, so equity stays strictly positive
    bar_returns=st.lists(
        st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=60,
    ),
    longs=st.lists(st.sampled_from([0.0, 1.0]), min_size=3, max_size=60),
)
def test_long_only_equity_is_finite_and_positive(
    bar_returns: list[float], longs: list[float]
) -> None:
    n = min(len(bar_returns), len(longs))
    price = 100.0
    closes = []
    for r in bar_returns[:n]:
        price *= 1 + r
        closes.append(price)
    prices = _prices(closes)
    signals = pd.Series(longs[:n], index=prices.index)
    result = BacktestEngine(cost_rate=0.001).run(prices, signals)
    eq = result.equity_curve.to_numpy()
    assert np.isfinite(eq).all()
    assert (eq > 0).all()
    assert -1.0 <= result.metrics.max_drawdown <= 0.0


@settings(deadline=None)
@given(
    returns=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=100,
    )
)
def test_sharpe_ratio_is_finite_for_non_constant_series(returns: list[float]) -> None:
    # §8 invariant #2: Sharpe is finite for a non-constant return series.
    assume(len(set(returns)) > 1)
    result = sharpe_ratio(pd.Series(returns))
    assert np.isfinite(result)


@settings(deadline=None)
@given(
    returns=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=100,
    )
)
def test_sortino_ratio_is_finite_when_a_return_falls_below_target(
    returns: list[float],
) -> None:
    # §8 invariant #11: Sortino is finite whenever at least one return falls below the target
    # (0.0 by default), i.e. downside deviation is strictly positive.
    assume(any(r < 0.0 for r in returns))
    result = sortino_ratio(pd.Series(returns))
    assert np.isfinite(result)


@settings(deadline=None)
@given(
    annualized_return=st.floats(
        min_value=-1.0, max_value=5.0, allow_nan=False, allow_infinity=False
    ),
    max_dd=st.floats(min_value=-1.0, max_value=-1e-6, allow_nan=False, allow_infinity=False),
)
def test_calmar_ratio_is_finite_when_max_drawdown_is_nonzero(
    annualized_return: float, max_dd: float
) -> None:
    # §8 invariant #12: Calmar is finite whenever max_drawdown != 0.0.
    result = calmar_ratio(annualized_return=annualized_return, max_drawdown=max_dd)
    assert np.isfinite(result)


@settings(deadline=None)
@given(
    returns=st.lists(
        st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=50,
    )
)
def test_annualized_return_has_compounded_total_return_sign(returns: list[float]) -> None:
    # ADR-110: geometric annualization is a monotone transform of positive terminal wealth, so
    # it can never reverse the sign of the complete compounded return path.
    series = pd.Series(returns, dtype="float64")

    metrics = BacktestMetrics.from_series(series)

    assert np.sign(metrics.annualized_return) == np.sign(metrics.total_return)


@settings(deadline=None)
@given(
    returns=st.lists(
        st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
        min_size=TRADING_DAYS,
        max_size=TRADING_DAYS * 2,
    )
)
def test_sharpe_confidence_interval_always_brackets_the_point_estimate(
    returns: list[float],
) -> None:
    # ADR-109: a symmetric z-interval around the point estimate must contain it by construction,
    # for any return series long enough to produce an interval at all.
    assume(len(set(returns)) > 1)
    series = pd.Series(returns)
    ci = sharpe_confidence_interval(series)
    assert ci is not None
    assert ci.lower <= sharpe_ratio(series) <= ci.upper


@settings(deadline=None)
@given(
    bar_returns=st.lists(
        st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=40,
    ),
    raw_signals=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=40,
    ),
    cost_rates=st.lists(
        st.floats(min_value=0.0, max_value=0.02, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
def test_transaction_costs_never_increase_total_return(
    bar_returns: list[float], raw_signals: list[float], cost_rates: list[float]
) -> None:
    # §8 invariant #7: transaction costs always reduce (never increase) net returns. Bounds on
    # bar_returns/cost_rates keep every per-bar net factor (1 + net) strictly positive, which is
    # what makes cumulative equity monotone in cost_rate an exact property, not just a trend.
    n = min(len(bar_returns), len(raw_signals))
    price = 100.0
    closes = []
    for r in bar_returns[:n]:
        price *= 1 + r
        closes.append(price)
    prices = _prices(closes)
    signals = pd.Series(raw_signals[:n], index=prices.index)
    returns_by_cost = [
        BacktestEngine(cost_rate=c).run(prices, signals).metrics.total_return
        for c in sorted(cost_rates)
    ]
    for earlier, later in pairwise(returns_by_cost):
        assert earlier >= later - 1e-9
