"""Risk analysis over Monte Carlo GBM paths (ADR-014 Phase 0): from a strategy's realized
daily returns, estimate the distribution of outcomes over a horizon and report loss/drawdown
probabilities. Deterministic under a fixed seed; probabilities are genuine invariants."""

import numpy as np
import pandas as pd
import pytest

from app.research.simulation.risk import MonteCarloRisk, analyze_strategy_risk


def _returns(mu_daily: float, sigma_daily: float, n: int = 504, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.Series(rng.normal(mu_daily, sigma_daily, n), index=idx)


def test_analyze_strategy_risk_is_deterministic_under_seed() -> None:
    r = _returns(0.0005, 0.01)
    a = analyze_strategy_risk(r, horizon_days=126, n_paths=5000, loss_threshold=0.2, seed=42)
    b = analyze_strategy_risk(r, horizon_days=126, n_paths=5000, loss_threshold=0.2, seed=42)
    assert a == b
    assert isinstance(a, MonteCarloRisk)


def test_analyze_strategy_risk_probabilities_are_in_unit_interval() -> None:
    r = _returns(0.0003, 0.012)
    res = analyze_strategy_risk(r, horizon_days=252, n_paths=8000, loss_threshold=0.15, seed=7)
    assert 0.0 <= res.prob_terminal_loss <= 1.0
    assert 0.0 <= res.prob_max_drawdown_exceeds <= 1.0
    # Terminal loss requires ending below -X; a drawdown of -X can happen intra-horizon even
    # when the path recovers, so max-drawdown breach is always at least as likely.
    assert res.prob_max_drawdown_exceeds >= res.prob_terminal_loss


def test_analyze_strategy_risk_percentiles_are_ordered() -> None:
    res = analyze_strategy_risk(
        _returns(0.0004, 0.01), horizon_days=252, n_paths=8000, loss_threshold=0.2, seed=1
    )
    assert res.terminal_return_p5 <= res.terminal_return_p50 <= res.terminal_return_p95
    assert res.horizon_days == 252
    assert res.n_paths == 8000
    assert res.loss_threshold == 0.2


def test_analyze_strategy_risk_higher_vol_raises_loss_probability() -> None:
    # Same drift, more volatility => fatter tails => a bigger loss is more probable.
    low = analyze_strategy_risk(
        _returns(0.0003, 0.008), horizon_days=252, n_paths=8000, loss_threshold=0.2, seed=3
    )
    high = analyze_strategy_risk(
        _returns(0.0003, 0.02), horizon_days=252, n_paths=8000, loss_threshold=0.2, seed=3
    )
    assert high.prob_terminal_loss > low.prob_terminal_loss


def test_analyze_strategy_risk_rejects_bad_inputs() -> None:
    r = _returns(0.0003, 0.01)
    with pytest.raises(ValueError):
        analyze_strategy_risk(r, horizon_days=0, n_paths=100, loss_threshold=0.2)
    with pytest.raises(ValueError):
        analyze_strategy_risk(r, horizon_days=10, n_paths=0, loss_threshold=0.2)
    with pytest.raises(ValueError):
        analyze_strategy_risk(r, horizon_days=10, n_paths=100, loss_threshold=0.0)
    with pytest.raises(ValueError):
        analyze_strategy_risk(r, horizon_days=10, n_paths=100, loss_threshold=1.5)
    with pytest.raises(ValueError):
        analyze_strategy_risk(
            pd.Series([0.01], dtype=float), horizon_days=10, n_paths=100, loss_threshold=0.2
        )
