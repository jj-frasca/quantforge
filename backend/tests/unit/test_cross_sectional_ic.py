"""Rank information coefficient for cross-sectional signals (ADR-035). The IC is the per-date
Spearman correlation between the signal cross-section at t and the returns realized from t to t+1
— a direct measurement of the only claim a cross-sectional strategy makes (that its ranking is
informative), independent of how the portfolio happened to be constructed. It is a DIAGNOSTIC:
nothing gates, selects, or sizes on it."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.ic import ICSummary, rank_ic, summarize_ic


def _prices(n_dates: int, n_symbols: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0005, 0.01, (n_dates, n_symbols))
    prices = 100.0 * np.cumprod(1.0 + steps, axis=0)
    idx = pd.date_range("2015-01-01", periods=n_dates, freq="B", tz="UTC")
    cols = [f"S{i}" for i in range(n_symbols)]
    return pd.DataFrame(prices, index=idx, columns=cols)


def test_a_perfectly_prescient_signal_has_ic_of_one() -> None:
    # The signal IS next bar's return, so its ranking is exactly the return ranking every date.
    prices = _prices(30, 5, 0)
    forward = prices.pct_change().shift(-1)
    ic = rank_ic(forward, prices)
    assert len(ic) == len(prices) - 1  # every date but the last, which has no FORWARD return
    assert np.allclose(ic.to_numpy(), 1.0)


def test_an_inverted_signal_has_ic_of_minus_one() -> None:
    prices = _prices(30, 5, 1)
    ic = rank_ic(-prices.pct_change().shift(-1), prices)
    assert np.allclose(ic.to_numpy(), -1.0)


def test_ic_uses_the_next_bar_not_the_current_one() -> None:
    # A signal equal to the CURRENT bar's return would score 1.0 if the causality were off by one.
    prices = _prices(40, 6, 2)
    ic = rank_ic(prices.pct_change(), prices)
    assert not np.allclose(ic.to_numpy(), 1.0)


def test_ic_is_invariant_to_a_monotonic_rescaling_of_the_signal() -> None:
    prices = _prices(40, 6, 3)
    signal = prices.pct_change(5)
    pd.testing.assert_series_equal(rank_ic(signal, prices), rank_ic(signal * 3.0 + 7.0, prices))


def test_dates_with_a_constant_signal_are_dropped_not_scored_zero() -> None:
    # A flat cross-section has no ranking, so its correlation is undefined. Recording it as 0.0
    # would drag the mean IC toward the null and manufacture a "no information" observation.
    prices = _prices(20, 4, 4)
    signal = prices.pct_change(3)
    signal.iloc[5] = 1.0  # every name identical on this date
    ic = rank_ic(signal, prices)
    assert prices.index[5] not in ic.index
    # 20 dates - 3 warmup NaNs - the last (no forward return) - the flat date
    assert len(ic) == len(prices) - 5


def test_dates_with_fewer_than_two_ranked_names_are_dropped() -> None:
    prices = _prices(20, 4, 5)
    signal = prices.pct_change(3)
    signal.iloc[7, 1:] = np.nan  # only one name is scorable that date
    ic = rank_ic(signal, prices)
    assert prices.index[7] not in ic.index


def test_ic_ignores_names_the_signal_cannot_score() -> None:
    prices = _prices(30, 5, 6)
    forward = prices.pct_change().shift(-1)
    signal = forward.copy()
    signal.iloc[:, 4] = np.nan  # unscorable name: excluded, so the rest still rank perfectly
    assert np.allclose(rank_ic(signal, prices).to_numpy(), 1.0)


def test_rank_ic_requires_aligned_symbols() -> None:
    prices = _prices(10, 3, 7)
    with pytest.raises(ValueError, match="columns"):
        rank_ic(prices.pct_change().rename(columns={"S0": "ZZ"}), prices)


def test_summarize_ic_reports_mean_ir_t_stat_and_hit_rate() -> None:
    idx = pd.date_range("2020-01-01", periods=4, freq="B", tz="UTC")
    series = pd.Series([0.2, -0.1, 0.4, 0.1], index=idx)
    summary = summarize_ic(series)
    assert summary is not None
    assert summary.n_periods == 4
    assert summary.mean == pytest.approx(0.15)
    assert summary.std == pytest.approx(float(np.std(series.to_numpy(), ddof=1)))
    assert summary.information_ratio == pytest.approx(summary.mean / summary.std)
    assert summary.t_stat == pytest.approx(summary.information_ratio * 2.0)
    assert summary.hit_rate == pytest.approx(0.75)


def test_summarize_ic_is_none_when_there_is_nothing_to_summarize() -> None:
    # One date cannot produce a dispersion estimate, so there is no IR and no t-stat to report.
    idx = pd.date_range("2020-01-01", periods=1, freq="B", tz="UTC")
    assert summarize_ic(pd.Series([0.3], index=idx)) is None
    assert summarize_ic(pd.Series(dtype=float)) is None


def test_summarize_ic_survives_a_zero_dispersion_series() -> None:
    idx = pd.date_range("2020-01-01", periods=3, freq="B", tz="UTC")
    summary = summarize_ic(pd.Series([0.25, 0.25, 0.25], index=idx))
    assert summary is not None
    assert summary.mean == pytest.approx(0.25)
    assert np.isfinite(summary.information_ratio)


def test_ic_summary_is_frozen() -> None:
    summary = ICSummary(
        mean=0.1, std=0.2, information_ratio=0.5, t_stat=1.0, hit_rate=0.6, n_periods=4
    )
    with pytest.raises(ValueError, match="frozen"):
        summary.mean = 0.9  # type: ignore[misc]


@settings(max_examples=30, deadline=None)
@given(st.integers(min_value=0, max_value=2**31 - 1), st.integers(min_value=3, max_value=8))
def test_ic_is_always_a_correlation(seed: int, n_symbols: int) -> None:
    prices = _prices(60, n_symbols, seed)
    ic = rank_ic(prices.pct_change(10), prices)
    assert ((ic >= -1.0000001) & (ic <= 1.0000001)).all()
