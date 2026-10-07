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
    assert ci.assumption == "iid_normal"


@pytest.mark.parametrize("confidence", [np.nan, -0.1, 0.0, 1.0, 1.1])
def test_sharpe_confidence_interval_rejects_invalid_confidence(confidence: float) -> None:
    returns = pd.Series(np.linspace(-0.01, 0.01, TRADING_DAYS))
    with pytest.raises(ValueError, match="confidence"):
        sharpe_confidence_interval(returns, confidence=confidence)


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
    # it can never reverse the sign of the complete compounded return path. True in exact
    # arithmetic, but total_return and annualized_return scale the SAME log-growth sum by
    # different factors (1 vs TRADING_DAYS/n) before exponentiating, so a log-growth magnitude
    # near float64's epsilon (~2.22e-16) can round to exactly zero on one side and to a tiny
    # nonzero residue on the other (ADR-121/FINDING-049) — that residue is financially
    # meaningless (<1e-9 of any real return) and not the sign reversal this property guards
    # against, so skip only the case where BOTH sides are already indistinguishable from zero.
    series = pd.Series(returns, dtype="float64")

    metrics = BacktestMetrics.from_series(series)
    negligible = 1e-9
    assume(abs(metrics.total_return) > negligible or abs(metrics.annualized_return) > negligible)

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


@pytest.mark.parametrize(
    "index",
    [
        pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-02"], utc=True),
        pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02"], utc=True),
        pd.Index([2, 1, 0]),
        pd.Index([0, 0, 1]),
    ],
)
def test_backtest_rejects_noncausal_price_calendar(index: pd.Index) -> None:
    prices = pd.Series([100.0, 121.0, 110.0], index=index)
    signals = pd.Series([0.0, 1.0, 0.0], index=index)
    with pytest.raises(ValueError, match="price calendar"):
        BacktestEngine(cost_rate=0).run(prices, signals)


def test_run_strategy_rejects_noncausal_price_calendar() -> None:
    index = pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-02"], utc=True)
    frame = pd.DataFrame({"close": [100.0, 121.0, 110.0]}, index=index)
    with pytest.raises(ValueError, match="price calendar"):
        BacktestEngine().run_strategy(frame, SMAStrategy(fast=1, slow=2))


@pytest.mark.parametrize("index", [pd.Index([0, 2, 4]), pd.date_range("2026-01-01", periods=3)])
def test_backtest_preserves_sparse_signal_alignment_on_ordered_generic_calendar(
    index: pd.Index,
) -> None:
    prices = pd.Series([100.0, 110.0, 121.0], index=index)
    signals = pd.Series([2.0], index=index[:1])
    result = BacktestEngine(cost_rate=0).run(prices, signals)
    np.testing.assert_allclose(result.returns, [0, 0.1, 0])
    np.testing.assert_array_equal(result.position, [1, 0, 0])


@given(st.permutations([0, 1, 2]))
def test_backtest_calendar_order_is_required_for_causal_lag(order: list[int]) -> None:
    prices = pd.Series([100.0, 110.0, 121.0], index=pd.Index(order))
    signals = pd.Series(1.0, index=prices.index)
    if order == [0, 1, 2]:
        result = BacktestEngine(cost_rate=0).run(prices, signals)
        assert result.metrics.total_return == pytest.approx(0.21)
    else:
        with pytest.raises(ValueError, match="price calendar"):
            BacktestEngine(cost_rate=0).run(prices, signals)


@pytest.mark.parametrize("n_rows", [0, 1])
def test_backtest_preserves_empty_and_single_row_calendars(n_rows: int) -> None:
    prices = pd.Series([100.0] * n_rows, dtype=float)
    signals = pd.Series([0.0] * n_rows, dtype=float)
    result = BacktestEngine().run(prices, signals)
    assert len(result.equity_curve) == n_rows
    assert result.n_trades == 0
    assert result.metrics.total_return == 0


@pytest.mark.parametrize("name", ["initial_capital", "cost_rate"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_backtest_rejects_nonfinite_config(name: str, value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        BacktestEngine(**{name: value})


@pytest.mark.parametrize(
    "capital,cost,prices",
    [
        (np.finfo(float).max, 0.0, [100.0, 110.0]),
        (float.fromhex("0x0.0000000000001p-1022"), 0.9, [100.0, 100.0]),
    ],
)
def test_backtest_rejects_unrepresentable_scaled_wealth(
    capital: float, cost: float, prices: list[float]
) -> None:
    price_series = pd.Series(prices)
    with pytest.raises(ValueError, match="equity"):
        BacktestEngine(initial_capital=capital, cost_rate=cost).run(
            price_series, pd.Series(1.0, index=price_series.index)
        )


@pytest.mark.parametrize("capital", [np.finfo(float).max, float.fromhex("0x0.0000000000001p-1022")])
def test_backtest_preserves_representable_extreme_flat_wealth(capital: float) -> None:
    result = BacktestEngine(initial_capital=capital, cost_rate=0).run(
        pd.Series([100.0, 100.0]), pd.Series([1.0, 1.0])
    )
    np.testing.assert_array_equal(result.equity_curve, [capital, capital])


def test_backtest_declines_nonfinite_curve_after_public_capital_mutation() -> None:
    engine = BacktestEngine()
    engine.initial_capital = np.nan
    with pytest.raises(ValueError, match="equity"):
        engine.run(pd.Series([100.0, 100.0]), pd.Series([0.0, 0.0]))


@given(capital=st.floats(min_value=1e-250, max_value=1e250, allow_nan=False, allow_infinity=False))
def test_backtest_representable_wealth_preserves_capital_scale(capital: float) -> None:
    prices = pd.Series([100.0, 101.0, 100.0])
    signals = pd.Series([1.0, 1.0, 1.0])
    reference = BacktestEngine(initial_capital=1).run(prices, signals)
    scaled = BacktestEngine(initial_capital=capital).run(prices, signals)
    assert np.isfinite(scaled.equity_curve).all()
    assert (scaled.equity_curve > 0).all()
    np.testing.assert_allclose(scaled.equity_curve / capital, reference.equity_curve, rtol=1e-14)
    assert scaled.metrics == reference.metrics


@pytest.mark.parametrize(
    "values",
    [
        [100.0, np.nan, 110.0],
        [np.nan, 100.0, 110.0],
        [100.0, 110.0, np.nan],
        [-100.0, -110.0, -121.0],
        [0.0],
        [np.inf],
        [-np.inf],
        [np.nan],
    ],
)
@pytest.mark.parametrize("exposure", [0.0, 1.0])
def test_backtest_rejects_invalid_price_observations(values: list[float], exposure: float) -> None:
    prices = _prices(values)
    with pytest.raises(ValueError, match="prices"):
        BacktestEngine(cost_rate=0).run(prices, pd.Series(exposure, index=prices.index))


@pytest.mark.parametrize(
    "prices",
    [
        pd.Series([True, True]),
        pd.Series([100, 110], dtype=object),
        pd.Series(["100", "110"]),
        pd.Series([100 + 0j, 110 + 0j]),
        pd.Series([100, pd.NA, 110], dtype="Float64"),
        pd.Series([100, pd.NA, 110], dtype="Int64"),
    ],
)
def test_backtest_rejects_nonreal_or_missing_nullable_prices(prices: pd.Series) -> None:
    with pytest.raises(ValueError, match="prices"):
        BacktestEngine(cost_rate=0).run(prices, pd.Series(1.0, index=prices.index))


@pytest.mark.parametrize("dtype", ["float64", "int64", "Float64", "Int64"])
def test_backtest_preserves_complete_numeric_prices(dtype: str) -> None:
    prices = pd.Series([100, 110, 121], dtype=dtype)
    result = BacktestEngine(initial_capital=100, cost_rate=0).run(
        prices, pd.Series(1.0, index=prices.index)
    )
    np.testing.assert_allclose(result.returns.to_numpy(dtype=float), [0.0, 0.1, 0.1])
    np.testing.assert_allclose(result.equity_curve.to_numpy(dtype=float), [100, 110, 121])
    assert result.metrics.total_return == pytest.approx(0.21)


@given(st.floats(min_value=-1e100, max_value=0, allow_nan=False, allow_infinity=False))
def test_backtest_rejects_nonpositive_price_at_every_position(price: float) -> None:
    for row in range(3):
        prices = _prices([100, 100, 100])
        prices.iloc[row] = price
        with pytest.raises(ValueError, match="prices"):
            BacktestEngine(cost_rate=0).run(prices, pd.Series(1.0, index=prices.index))


@pytest.mark.parametrize("padding", [126, 882])
def test_sharpe_interval_rejects_missing_history_padding(padding: int) -> None:
    returns = pd.Series(
        list(np.random.default_rng(123).normal(0.001, 0.01, 126)) + [np.nan] * padding
    )
    with pytest.raises(ValueError, match="returns"):
        sharpe_confidence_interval(returns)


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([np.nan]),
        pd.Series([np.inf] * 252),
        pd.Series([True, False] * 126),
        pd.Series([0.01] * 252, dtype=object),
        pd.Series([".01"] * 252),
        pd.Series([0.01 + 1j] * 252),
        pd.Series([0.01, pd.NA] * 126, dtype="Float64"),
    ],
)
def test_sharpe_interval_rejects_invalid_return_evidence(returns: pd.Series) -> None:
    with pytest.raises(ValueError, match="returns"):
        sharpe_confidence_interval(returns)


@given(padding=st.integers(min_value=126, max_value=1000))
def test_sharpe_interval_missing_padding_cannot_manufacture_precision(padding: int) -> None:
    returns = pd.Series([-0.01, 0.01] * 63 + [np.nan] * padding)
    with pytest.raises(ValueError, match="returns"):
        sharpe_confidence_interval(returns)


@pytest.mark.parametrize("dtype", ["float64", "int64", "Float64", "Int64"])
def test_sharpe_interval_preserves_complete_signed_numeric_evidence(dtype: str) -> None:
    returns = pd.Series([-2, -1, 0, 1, 2] * 60, dtype=dtype)
    actual = sharpe_confidence_interval(returns)
    expected = sharpe_confidence_interval(returns.astype(float))
    assert actual == expected
    assert actual is not None
    assert actual.assumption == "iid_normal"


def test_sharpe_interval_validates_confidence_before_return_evidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        sharpe_confidence_interval(pd.Series([np.nan]), confidence=1)


def test_sharpe_interval_nearest_valid_confidence_has_finite_bounds() -> None:
    confidence = float(np.nextafter(1.0, 0.0))
    ci = sharpe_confidence_interval(pd.Series([-0.01, 0.01] * 126), confidence=confidence)
    assert ci is not None
    assert np.isfinite([ci.lower, ci.upper]).all()
    assert ci.lower == -ci.upper
    assert ci.confidence == confidence


@given(
    confidence=st.floats(
        min_value=0.999,
        max_value=float(np.nextafter(1.0, 0.0)),
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_sharpe_interval_high_confidence_matches_forward_gaussian_tail(confidence: float) -> None:
    from math import erfc, sqrt

    # Zero Sharpe over exactly one year gives unit standard error; upper is the quantile.
    ci = sharpe_confidence_interval(pd.Series([-0.01, 0.01] * 126), confidence=confidence)
    assert ci is not None
    assert np.isfinite([ci.lower, ci.upper]).all()
    measured_tail = erfc(ci.upper / sqrt(2)) / 2
    assert measured_tail == pytest.approx((1 - confidence) / 2, rel=1e-12, abs=0)


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([np.nan]),
        pd.Series([0.01, np.nan]),
        pd.Series([0.01, np.inf]),
        pd.Series([-np.inf]),
        pd.Series([True, False]),
        pd.Series([], dtype=bool),
        pd.Series([], dtype=object),
        pd.Series([True, pd.NA], dtype="boolean"),
        pd.Series([0.02, 0.02, np.nan]),
        pd.Series([0.01 + 1j, 0.02 + 2j]),
        pd.Series(["0.01", "0.02"]),
        pd.Series([0.01, pd.NA], dtype="Float64"),
    ],
)
def test_standalone_sharpe_rejects_invalid_source_evidence(returns: pd.Series) -> None:
    with pytest.raises(ValueError, match="returns must be"):
        sharpe_ratio(returns)


@given(st.integers(min_value=1, max_value=100))
def test_standalone_sharpe_rejects_missing_padding(padding: int) -> None:
    returns = pd.Series([0.01, -0.02, 0.03] + [np.nan] * padding)
    with pytest.raises(ValueError, match="finite and complete"):
        sharpe_ratio(returns)


@pytest.mark.parametrize("values", [[], [0.01], [0.02, 0.02], [-1.5, -1.0, 0.25, 2.0]])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_standalone_sharpe_preserves_valid_signed_and_degenerate_samples(
    values: list[float], dtype: str
) -> None:
    returns = pd.Series(values, dtype=dtype)
    expected = (
        0.0
        if len(values) < 2 or np.std(values, ddof=1) == 0.0
        else float(np.sqrt(252) * np.mean(values) / np.std(values, ddof=1))
    )
    assert sharpe_ratio(returns) == pytest.approx(expected)


@pytest.mark.parametrize("metric", [total_return, annualized_return])
@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([True, False]),
        pd.Series(["0.01", "-0.02"]),
        pd.Series([0.01, -0.02], dtype=object),
        pd.Series([0.01 + 1j, -0.02 + 2j]),
        pd.Series([], dtype=bool),
        pd.Series([], dtype=object),
        pd.Series([], dtype=complex),
    ],
)
def test_compounded_return_rejects_invalid_source_before_conversion(metric, returns) -> None:
    with pytest.raises(ValueError, match="real nonboolean numeric"):
        metric(returns)


@pytest.mark.parametrize("metric", [total_return, annualized_return])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_compounded_return_preserves_complete_nullable_wealth_oracle(metric, dtype) -> None:
    values = [-0.01, 0.02, -0.03, 0.04] * 63
    # Exactly one trading year makes both estimators equal to the independent wealth product.
    expected = float(np.prod(1.0 + np.asarray(values)) - 1.0)
    assert metric(pd.Series(values, dtype=dtype)) == pytest.approx(expected, rel=1e-12)
    assert metric(pd.Series([], dtype=dtype)) == 0.0


@pytest.mark.parametrize("metric", [total_return, annualized_return])
@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, pd.NA])
def test_compounded_return_rejects_incomplete_nullable_source(metric, invalid) -> None:
    with pytest.raises(ValueError):
        metric(pd.Series([0.01, invalid], dtype="Float64"))


@pytest.mark.parametrize("target", [np.nan, np.inf, -np.inf, True, 0.01 + 1j, "0.01"])
def test_sortino_rejects_invalid_target_even_without_history(target) -> None:
    with pytest.raises(ValueError, match="target must be"):
        sortino_ratio(pd.Series([], dtype=float), target=target)


@pytest.mark.parametrize(
    "returns",
    [
        pd.Series([np.nan]),
        pd.Series([0.01, np.nan, -0.02]),
        pd.Series([0.01, np.inf]),
        pd.Series([True, False]),
        pd.Series([0.01 + 1j, -0.02 + 2j]),
        pd.Series(["0.01", "-0.02"]),
        pd.Series([], dtype=object),
        pd.Series([0.02, pd.NA], dtype="Float64"),
    ],
)
def test_sortino_rejects_malformed_source_before_shortcuts(returns) -> None:
    with pytest.raises(ValueError, match="returns must be"):
        sortino_ratio(returns)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("target", [-0.5, 0.0, 0.01, 1])
def test_sortino_preserves_signed_nullable_full_sample_downside_oracle(dtype, target) -> None:
    from math import sqrt

    values = [-1.5, -1.0, 0.25, 2.0]
    excess = [value - target for value in values]
    downside = sqrt(sum(min(value, 0.0) ** 2 for value in excess) / len(values))
    expected = sqrt(252) * (sum(excess) / len(excess)) / downside
    assert sortino_ratio(pd.Series(values, dtype=dtype), target=target) == pytest.approx(expected)


def test_sortino_invalid_target_precedes_invalid_source() -> None:
    with pytest.raises(ValueError, match="target must be"):
        sortino_ratio(pd.Series([np.nan]), target=np.nan)


@pytest.mark.parametrize("target", [np.bool_(True), 10**400])
def test_sortino_refuses_boolean_or_unrepresentable_real_target(target) -> None:
    with pytest.raises(ValueError, match="target must be"):
        sortino_ratio(pd.Series([], dtype=float), target=target)


def test_sortino_preserves_fraction_and_numpy_scalar_target() -> None:
    from fractions import Fraction

    returns = pd.Series([0.01, -0.02, 0.03])
    expected = sortino_ratio(returns, target=0.01)
    assert sortino_ratio(returns, target=Fraction(1, 100)) == pytest.approx(expected)
    assert sortino_ratio(returns, target=np.float64(0.01)) == pytest.approx(expected)


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, True, "0.1", 0.1 + 1j])
def test_calmar_rejects_invalid_numerator_before_zero_drawdown(invalid) -> None:
    with pytest.raises(ValueError, match="Calmar inputs must be"):
        calmar_ratio(annualized_return=invalid, max_drawdown=0.0)


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, False, "0.1", 0.1 + 1j])
def test_calmar_rejects_invalid_drawdown_scalar(invalid) -> None:
    with pytest.raises(ValueError, match="Calmar inputs must be"):
        calmar_ratio(annualized_return=0.2, max_drawdown=invalid)


@pytest.mark.parametrize("numerator", [1e308, -1e308])
def test_calmar_refuses_nonfinite_native_quotient(numerator) -> None:
    with pytest.raises(ValueError, match="Calmar ratio must be finite"):
        calmar_ratio(annualized_return=numerator, max_drawdown=-1e-308)


def test_composed_metrics_refuse_overflowed_calmar() -> None:
    with pytest.raises(ValueError, match="Calmar ratio must be finite"):
        BacktestMetrics.from_series(pd.Series([-1e-8, 270.0]))


@pytest.mark.parametrize("drawdown", [-0.125, 0.125])
@pytest.mark.parametrize("numerator", [-0.25, 0.0, 0.25])
def test_calmar_preserves_exact_finite_ratio_and_zero_convention(numerator, drawdown) -> None:
    from fractions import Fraction

    expected = float(Fraction(numerator) / abs(Fraction(drawdown)))
    assert calmar_ratio(numerator, drawdown) == expected
    assert calmar_ratio(numerator, 0.0) == 0.0


def test_calmar_preserves_fraction_and_numpy_scalar_inputs() -> None:
    from fractions import Fraction

    assert calmar_ratio(Fraction(1, 4), Fraction(-1, 8)) == 2.0
    assert calmar_ratio(np.float64(0.25), np.float64(-0.125)) == 2.0


@pytest.mark.parametrize("invalid", [np.bool_(True), 10**400])
def test_calmar_rejects_boolean_or_unrepresentable_numerator(invalid) -> None:
    with pytest.raises(ValueError, match="Calmar inputs must be"):
        calmar_ratio(invalid, 0.0)
