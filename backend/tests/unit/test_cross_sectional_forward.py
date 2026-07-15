"""Cross-sectional forward-testing (ADR-025). A cross-sectional graduate is a whole dollar-neutral
long/short portfolio, so it is forward-tested by continuing to compute its engine `portfolio_returns`
on bars AFTER its freeze boundary and benchmarking against the equal-weight long-only universe (the
same benchmark ADR-024 used at the holdout). Everything is pure over injectable panels -- no network,
no look-ahead (weights at t use prices <= t)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.forward import (
    CrossSectionalForwardScore,
    CrossSectionalPosition,
    score_forward,
)


def _noise_panel(n: int = 800, n_symbols: int = 6, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, (n, n_symbols)), axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def _persistent_momentum_panel(n: int = 800, n_symbols: int = 6, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    drifts = np.linspace(-0.0010, 0.0010, n_symbols)
    steps = rng.normal(0.0, 0.006, (n, n_symbols)) + drifts
    prices = 100.0 * np.cumprod(1.0 + steps, axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def _momentum_position(panel: pd.DataFrame, split: int = 400) -> CrossSectionalPosition:
    return CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[split].to_pydatetime(),
    )


def test_score_forward_scores_only_post_freeze_bars_vs_equal_weight_benchmark() -> None:
    panel = _persistent_momentum_panel()
    pos = _momentum_position(panel, split=400)
    score = score_forward(pos, panel)
    assert isinstance(score, CrossSectionalForwardScore)
    # 800 bars, frozen at index 400 -> bars strictly after (401..799) = 399 scored.
    assert score.forward_bars == len(panel) - 401
    assert score.as_of == panel.index.max().to_pydatetime()
    assert score.beats_benchmark == (score.forward_sharpe > score.benchmark_sharpe)
    # a persistent long/short spread should beat holding the universe equal-weight, risk-adjusted.
    assert score.beats_benchmark is True
    # the equity curve has one point per forward bar; terminal == 1 + scalar total return.
    assert len(score.forward_equity) == score.forward_bars
    assert score.forward_equity[-1].strategy_equity == pytest.approx(1.0 + score.forward_return)
    assert score.forward_equity[-1].benchmark_equity == pytest.approx(1.0 + score.benchmark_return)


def test_score_forward_returns_zero_bar_score_before_any_forward_data() -> None:
    panel = _noise_panel()
    pos = CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index.max().to_pydatetime(),  # nothing strictly after the last bar
    )
    score = score_forward(pos, panel)
    assert score.forward_bars == 0
    assert score.forward_return == 0.0
    assert score.beats_benchmark is False
    assert score.forward_equity == []


def test_score_forward_reconstructs_value_factor_from_stored_scores() -> None:
    panel = _noise_panel()
    scores = {f"S{i}": float(i) / 6.0 for i in range(6)}
    pos = CrossSectionalPosition(
        strategy_name="xs_value",
        parameters={"quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[400].to_pydatetime(),
        value_scores=scores,
    )
    score = score_forward(pos, panel)
    assert score.forward_bars > 0


def test_score_forward_raises_on_unknown_strategy() -> None:
    panel = _noise_panel()
    pos = CrossSectionalPosition(
        strategy_name="bogus",
        parameters={"quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[400].to_pydatetime(),
    )
    with pytest.raises(ValueError, match="unknown cross-sectional strategy"):
        score_forward(pos, panel)


@settings(max_examples=25, deadline=None)
@given(cut=st.integers(min_value=1, max_value=200))
def test_score_forward_is_truncation_invariant_no_lookahead(cut: int) -> None:
    """Appending future bars cannot change already-scored forward returns (rank on t, trade t+1)."""
    panel = _persistent_momentum_panel(n=700)
    pos = _momentum_position(panel, split=300)
    truncated = panel.iloc[: len(panel) - cut]
    full_equity = score_forward(pos, panel).forward_equity
    trunc_equity = score_forward(pos, truncated).forward_equity
    for i in range(len(trunc_equity)):
        assert full_equity[i].strategy_equity == pytest.approx(trunc_equity[i].strategy_equity)
