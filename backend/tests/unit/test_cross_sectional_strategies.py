"""Cross-sectional signal producers + registry (ADR-024). Each strategy maps a price panel to a
signal panel where `signal[t, sym]` uses only prices <= t (built with `.shift`), so the engine's
no-lookahead contract holds. Momentum longs past winners, reversal longs recent losers, value ranks
on each name's (as-of) UndervaluationScore."""

import numpy as np
import pandas as pd
import pytest

from app.research.cross_sectional.registry import (
    CrossSectionalStrategy,
    default_strategies,
)
from app.research.cross_sectional.strategies import (
    alpha19_signal,
    alpha34_signal,
    composite_signal,
    cs_rank,
    cs_zscore,
    high_proximity_signal,
    low_volatility_signal,
    momentum_signal,
    quality_signal,
    residual_momentum_signal,
    reversal_signal,
    risk_adjusted_momentum_signal,
    value_signal,
)


def _prices(n_dates: int = 8, n_symbols: int = 3, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.01, (n_dates, n_symbols)), axis=0)
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def test_cs_rank_ranks_symbols_within_each_row_as_percentile() -> None:
    df = pd.DataFrame(
        {"A": [10.0, 5.0], "B": [20.0, 15.0], "C": [30.0, 25.0]},
        index=pd.date_range("2020-01-01", periods=2, freq="B", tz="UTC"),
    )
    ranked = cs_rank(df)
    # Each row ranks across symbols only; highest value -> 1.0, lowest -> 1/n.
    pd.testing.assert_series_equal(
        ranked.iloc[0],
        pd.Series({"A": 1 / 3, "B": 2 / 3, "C": 1.0}),
        check_names=False,
    )


def test_cs_rank_excludes_nan_and_ranks_over_valid_names_only() -> None:
    df = pd.DataFrame(
        {"A": [10.0], "B": [np.nan], "C": [30.0]},
        index=pd.date_range("2020-01-01", periods=1, freq="B", tz="UTC"),
    )
    ranked = cs_rank(df)
    assert ranked.iloc[0]["A"] == 0.5 and ranked.iloc[0]["C"] == 1.0
    assert np.isnan(ranked.iloc[0]["B"])  # unscorable name stays NaN, excluded by the ranker


def test_cs_rank_no_lookahead_truncation_invariant() -> None:
    # Cross-sectional rank is per-row (axis=1), so a row never sees other dates -> truncating the
    # future cannot change any past row's rank.
    prices = _prices(n_dates=12)
    full = cs_rank(prices)
    truncated = cs_rank(prices.iloc[:8])
    pd.testing.assert_frame_equal(full.iloc[:8], truncated)


def test_momentum_signal_is_trailing_return_and_warms_up_nan() -> None:
    prices = _prices()
    sig = momentum_signal(prices, lookback=3, skip=0)
    assert sig.iloc[:3].isna().all().all()  # first `lookback` rows have no trailing window
    expected = prices.iloc[3] / prices.iloc[0] - 1.0
    pd.testing.assert_series_equal(sig.iloc[3], expected, check_names=False)


def test_momentum_signal_skip_shifts_the_window_back() -> None:
    prices = _prices()
    sig = momentum_signal(prices, lookback=2, skip=1)
    assert sig.iloc[:3].isna().all().all()  # lookback + skip = 3 warmup rows
    expected = prices.iloc[2] / prices.iloc[0] - 1.0  # ends `skip` bars ago
    pd.testing.assert_series_equal(sig.iloc[3], expected, check_names=False)


def test_reversal_signal_is_negated_trailing_return() -> None:
    prices = _prices()
    pd.testing.assert_frame_equal(
        reversal_signal(prices, lookback=3), -momentum_signal(prices, lookback=3, skip=0)
    )


def test_value_signal_broadcasts_static_scores_across_dates() -> None:
    prices = _prices(n_symbols=3)
    scores = {"S0": 0.8, "S1": 0.2}  # S2 unscored
    sig = value_signal(prices, scores)
    assert sig.shape == prices.shape
    assert (sig["S0"] == 0.8).all() and (sig["S1"] == 0.2).all()
    assert sig["S2"].isna().all()  # unscored name -> NaN -> excluded by the ranker


def _low_vol_panel(n_dates: int = 40) -> pd.DataFrame:
    # S_calm has tiny wiggles, S_wild has large ones -> S_calm must score highest on -realized-vol.
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    calm = 100.0 * np.cumprod(1.0 + np.full(n_dates, 0.0005))  # deterministic, near-zero vol
    rng = np.random.default_rng(7)
    wild = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.05, n_dates))
    mid = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.02, n_dates))
    return pd.DataFrame({"S_calm": calm, "S_wild": wild, "S_mid": mid}, index=idx)


def test_low_volatility_signal_negates_trailing_realized_vol() -> None:
    prices = _prices()
    sig = low_volatility_signal(prices, vol_window=3)
    returns = prices.pct_change()
    expected = -returns.rolling(3).std()
    pd.testing.assert_frame_equal(sig, expected)


def test_low_volatility_signal_warms_up_nan() -> None:
    prices = _prices()
    sig = low_volatility_signal(prices, vol_window=4)
    assert sig.iloc[:4].isna().all().all()  # first `vol_window` rows have no full return window
    assert sig.iloc[4:].notna().all().all()


def test_low_volatility_signal_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=12)
    full = low_volatility_signal(prices, vol_window=3)
    truncated = low_volatility_signal(prices.iloc[:8], vol_window=3)
    pd.testing.assert_frame_equal(full.iloc[:8], truncated)


def test_low_volatility_signal_ranks_calm_name_on_top() -> None:
    prices = _low_vol_panel()
    sig = low_volatility_signal(prices, vol_window=10)
    assert sig.iloc[-1].idxmax() == "S_calm"  # long the lowest-vol name
    assert sig.iloc[-1].idxmin() == "S_wild"  # short the highest-vol name


def test_residual_momentum_signal_nets_out_own_trailing_drift() -> None:
    prices = _prices(n_dates=120)
    sig = residual_momentum_signal(prices, lookback=20, skip=5, mean_window=30)
    returns = prices.pct_change()
    residual = returns - returns.rolling(30).mean()
    expected = residual.rolling(20).sum().shift(5)
    pd.testing.assert_frame_equal(sig, expected)


def test_residual_momentum_signal_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=120)
    full = residual_momentum_signal(prices, lookback=20, skip=5, mean_window=30)
    truncated = residual_momentum_signal(prices.iloc[:90], lookback=20, skip=5, mean_window=30)
    pd.testing.assert_frame_equal(full.iloc[:90], truncated)


def test_risk_adjusted_momentum_signal_is_mean_over_vol() -> None:
    prices = _prices(n_dates=120)
    sig = risk_adjusted_momentum_signal(prices, lookback=20)
    returns = prices.pct_change()
    expected = returns.rolling(20).mean() / returns.rolling(20).std().replace(0.0, np.nan)
    pd.testing.assert_frame_equal(sig, expected)


def test_risk_adjusted_momentum_prefers_the_steadier_of_two_equal_return_names() -> None:
    # Two names end at the same cumulative return; STEADY rises smoothly, CHOPPY zig-zags there.
    # Risk-adjusted momentum (mean/vol) ranks the lower-volatility path higher.
    n = 60
    idx = pd.date_range("2020-01-01", periods=n, freq="B", tz="UTC")
    steady = 100.0 * (1.0 + 0.002) ** np.arange(n)
    chop = steady * (1.0 + 0.03 * np.sin(np.arange(n) * 1.7))  # same trend, added wobble
    prices = pd.DataFrame({"STEADY": steady, "CHOPPY": chop}, index=idx)
    sig = risk_adjusted_momentum_signal(prices, lookback=30)
    assert sig.iloc[-1]["STEADY"] > sig.iloc[-1]["CHOPPY"]


def test_risk_adjusted_momentum_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=120)
    full = risk_adjusted_momentum_signal(prices, lookback=20)
    truncated = risk_adjusted_momentum_signal(prices.iloc[:90], lookback=20)
    pd.testing.assert_frame_equal(full.iloc[:90], truncated)


def test_cs_zscore_standardizes_each_row_to_mean_zero() -> None:
    df = pd.DataFrame(
        {"A": [1.0, 2.0], "B": [2.0, 4.0], "C": [3.0, 6.0]},
        index=pd.date_range("2020-01-01", periods=2, freq="B", tz="UTC"),
    )
    z = cs_zscore(df)
    # each row: mean ~0, and the largest name has the highest z-score.
    assert z.iloc[0].mean() == pytest.approx(0.0, abs=1e-12)
    assert z.iloc[0].idxmax() == "C" and z.iloc[0].idxmin() == "A"


def test_cs_zscore_degenerate_row_is_nan() -> None:
    df = pd.DataFrame(
        {"A": [5.0], "B": [5.0], "C": [5.0]},  # zero cross-sectional std
        index=pd.date_range("2020-01-01", periods=1, freq="B", tz="UTC"),
    )
    assert cs_zscore(df).iloc[0].isna().all()


def test_composite_ranks_the_all_round_best_name_on_top() -> None:
    # STRONG trends up steadily (best momentum + 52w-high + residual mom, low vol); WEAK drifts down
    # choppily. The averaged z-score composite should rank STRONG highest, WEAK lowest.
    n = 200
    idx = pd.date_range("2018-01-01", periods=n, freq="B", tz="UTC")
    strong = 100.0 * (1.0 + 0.0015) ** np.arange(n)
    rng = np.random.default_rng(3)
    weak = 100.0 * np.cumprod(1.0 + rng.normal(-0.0005, 0.02, n))
    mid = 100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.01, n))
    prices = pd.DataFrame({"STRONG": strong, "WEAK": weak, "MID": mid}, index=idx)
    sig = composite_signal(prices, lookback=126)
    assert sig.iloc[-1].idxmax() == "STRONG"
    assert sig.iloc[-1].idxmin() == "WEAK"


def test_composite_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=200, n_symbols=5)
    full = composite_signal(prices, lookback=63)
    truncated = composite_signal(prices.iloc[:150], lookback=63)
    pd.testing.assert_frame_equal(full.iloc[:150], truncated)


def test_alpha34_combines_vol_ratio_and_reversal_ranks_shape_and_bounds() -> None:
    prices = _prices(n_dates=60, n_symbols=5)
    sig = alpha34_signal(prices, short_window=2, long_window=5)
    assert sig.shape == prices.shape
    # each of the two rank-inverse terms is in [0,1], so the sum is in [0,2] where defined.
    valid = sig.iloc[-1].dropna()
    assert ((valid >= 0.0) & (valid <= 2.0)).all()


def test_alpha34_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=120, n_symbols=5)
    full = alpha34_signal(prices, short_window=2, long_window=5)
    truncated = alpha34_signal(prices.iloc[:90], short_window=2, long_window=5)
    pd.testing.assert_frame_equal(full.iloc[:90], truncated)


def test_alpha19_fades_the_recent_move() -> None:
    # A name that rose over the last `change_lag` bars gets a negative sign contribution (fade).
    prices = _prices(n_dates=300, n_symbols=4)
    sig = alpha19_signal(prices, change_lag=7, sum_window=250)
    assert sig.shape == prices.shape
    assert sig.iloc[-1].notna().any()  # warm past sum_window


def test_alpha19_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=320, n_symbols=4)
    full = alpha19_signal(prices, change_lag=7, sum_window=250)
    truncated = alpha19_signal(prices.iloc[:300], change_lag=7, sum_window=250)
    pd.testing.assert_frame_equal(full.iloc[:300], truncated)


def test_default_strategies_are_price_only_without_scores() -> None:
    strategies = default_strategies()
    assert {"xs_momentum", "xs_reversal", "xs_low_volatility"} <= set(strategies)
    assert {"xs_residual_momentum", "xs_risk_adjusted_momentum", "xs_composite"} <= set(strategies)
    assert {"xs_alpha34", "xs_alpha19"} <= set(strategies)
    assert "xs_value" not in strategies
    assert all(isinstance(s, CrossSectionalStrategy) for s in strategies.values())
    assert all(len(s.param_grid) >= 1 for s in strategies.values())


def test_new_momentum_factors_registered_with_multi_config_grids() -> None:
    strategies = default_strategies()
    assert len(strategies["xs_residual_momentum"].param_grid) >= 2
    assert len(strategies["xs_risk_adjusted_momentum"].param_grid) >= 2


def test_low_volatility_is_registered_with_multi_config_grid() -> None:
    low_vol = default_strategies()["xs_low_volatility"]
    assert len(low_vol.param_grid) >= 2  # >= 2 configs so PBO is meaningful
    assert all("vol_window" in p for p in low_vol.param_grid)
    panel = low_vol.build(low_vol.param_grid[0])(_prices())
    assert panel.shape == _prices().shape


def _recent_loser_panel(n_dates: int = 60) -> pd.DataFrame:
    # S_loser slides over the trailing month while the others drift up -> a 21-bar reversal signal
    # (negated trailing return) must rank the recent loser highest (long the loser).
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    up = 100.0 * np.cumprod(1.0 + np.full(n_dates, 0.002))
    flat = 100.0 * np.cumprod(1.0 + np.full(n_dates, 0.0005))
    down = 100.0 * np.cumprod(1.0 + np.full(n_dates, -0.003))
    return pd.DataFrame({"S_up": up, "S_flat": flat, "S_loser": down}, index=idx)


def test_short_term_reversal_1m_is_registered_with_longer_horizon() -> None:
    strategies = default_strategies()
    rev_1m = strategies["xs_short_term_reversal_1m"]
    assert len(rev_1m.param_grid) >= 2  # >= 2 configs so PBO is meaningful
    lookbacks_1m = {int(p["lookback"]) for p in rev_1m.param_grid}
    short_lookbacks = {int(p["lookback"]) for p in strategies["xs_reversal"].param_grid}
    # Jegadeesh (1990): a distinctly longer (~1-month) horizon than the short xs_reversal.
    assert min(lookbacks_1m) > max(short_lookbacks)


def test_short_term_reversal_1m_ranks_recent_loser_on_top() -> None:
    prices = _recent_loser_panel()
    rev_1m = default_strategies()["xs_short_term_reversal_1m"]
    panel = rev_1m.build(rev_1m.param_grid[0])(prices)
    assert panel.iloc[-1].idxmax() == "S_loser"  # long the recent loser
    assert panel.iloc[-1].idxmin() == "S_up"  # short the recent winner


def _high_proximity_panel(n_dates: int = 40) -> pd.DataFrame:
    # S_high climbs monotonically (always at its trailing high -> ratio 1); S_faded rose then slid
    # back well below its peak (ratio < 1). Nearness-to-high must rank S_high top, S_faded bottom.
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    half = n_dates // 2
    high = 100.0 * np.cumprod(1.0 + np.full(n_dates, 0.004))
    faded = 100.0 * np.cumprod(
        1.0 + np.concatenate([np.full(half, 0.004), np.full(n_dates - half, -0.004)])
    )
    return pd.DataFrame({"S_high": high, "S_faded": faded}, index=idx)


def test_high_proximity_signal_is_price_over_trailing_high() -> None:
    prices = _prices()
    sig = high_proximity_signal(prices, window=3)
    expected = prices / prices.rolling(3).max()
    pd.testing.assert_frame_equal(sig, expected)


def test_high_proximity_signal_warms_up_nan() -> None:
    prices = _prices()
    sig = high_proximity_signal(prices, window=4)
    assert sig.iloc[:3].isna().all().all()  # first `window` - 1 rows have no full window
    assert sig.iloc[3:].notna().all().all()


def test_high_proximity_signal_no_lookahead_truncation_invariant() -> None:
    prices = _prices(n_dates=12)
    full = high_proximity_signal(prices, window=4)
    truncated = high_proximity_signal(prices.iloc[:8], window=4)
    pd.testing.assert_frame_equal(full.iloc[:8], truncated)


def test_high_proximity_signal_ranks_name_near_its_high_on_top() -> None:
    prices = _high_proximity_panel()
    sig = high_proximity_signal(prices, window=10)
    assert (sig["S_high"].iloc[10:] == 1.0).all()  # a monotone climber sits at its trailing high
    assert sig.iloc[-1].idxmax() == "S_high"  # long the name near its high
    assert sig.iloc[-1].idxmin() == "S_faded"  # short the name far below its high


def test_52w_high_is_registered_with_multi_config_grid() -> None:
    high = default_strategies()["xs_52w_high"]
    assert len(high.param_grid) >= 2  # >= 2 configs so PBO is meaningful
    assert all("window" in p for p in high.param_grid)
    panel = high.build(high.param_grid[0])(_prices(n_dates=300))
    assert panel.shape == _prices(n_dates=300).shape


def test_default_strategies_add_value_when_scores_given() -> None:
    strategies = default_strategies(value_scores={"S0": 0.8, "S1": 0.2})
    assert "xs_value" in strategies


def test_strategy_build_produces_a_working_signal_panel() -> None:
    prices = _prices()
    mom = default_strategies()["xs_momentum"]
    signal_fn = mom.build(mom.param_grid[0])
    panel = signal_fn(prices)
    assert panel.shape == prices.shape


def test_value_strategy_build_uses_the_scores() -> None:
    prices = _prices()
    value = default_strategies(value_scores={"S0": 0.9})["xs_value"]
    panel = value.build(value.param_grid[0])(prices)
    assert (panel["S0"] == 0.9).all()


def test_quality_signal_broadcasts_static_scores_across_dates() -> None:
    prices = _prices(n_symbols=3)
    scores = {"S0": 0.7, "S1": 0.3}  # S2 unscored
    sig = quality_signal(prices, scores)
    assert sig.shape == prices.shape
    assert (sig["S0"] == 0.7).all() and (sig["S1"] == 0.3).all()
    assert sig["S2"].isna().all()  # unscored name -> NaN -> excluded by the ranker


def test_default_strategies_add_quality_when_scores_given() -> None:
    strategies = default_strategies(quality_scores={"S0": 0.7, "S1": 0.3})
    assert "xs_quality" in strategies
    assert "xs_quality_value" not in strategies  # needs value scores too


def test_default_strategies_add_quality_value_only_when_both_given() -> None:
    both = default_strategies(
        value_scores={"S0": 0.8, "S1": 0.2}, quality_scores={"S0": 0.5, "S1": 0.4}
    )
    assert {"xs_quality", "xs_value", "xs_quality_value"} <= both.keys()


def test_quality_value_strategy_multiplies_quality_and_value() -> None:
    prices = _prices()
    strat = default_strategies(
        value_scores={"S0": 0.8, "S2": 0.5}, quality_scores={"S0": 0.5, "S1": 0.9}
    )["xs_quality_value"]
    panel = strat.build(strat.param_grid[0])(prices)
    assert (panel["S0"] == 0.8 * 0.5).all()  # only S0 has BOTH scores
    assert panel["S1"].isna().all() and panel["S2"].isna().all()
