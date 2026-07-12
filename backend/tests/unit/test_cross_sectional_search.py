"""Cross-sectional search + gate reuse (ADR-024). `run_cross_sectional_search` mirrors the
single-name `run_search` at the PORTFOLIO level: build each strategy's config grid, stack the
per-config portfolio return series into the (T, N) matrix the existing PBO/DSR/stability primitives
expect, pick the best by deflated Sharpe, score the finalist on the sealed holdout (full-panel
warmup, score the post-split slice, equal-weight long-only benchmark), and feed the unmodified
GraduationGate. A cross-sectional factor graduates exactly the way a single-name strategy does."""

import numpy as np
import pandas as pd
import pytest

from app.research.cross_sectional.search import (
    CrossSectionalExperiment,
    run_cross_sectional_search,
)
from app.research.lab.gate import GateConfig

_LENIENT = GateConfig(
    dsr_min=-100.0,
    pbo_max=1.01,
    stability_min=-1.0,
    holdout_sharpe_min=-100.0,
    require_beat_buy_and_hold=False,
)


def _noise_panel(n: int = 800, n_symbols: int = 6, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, (n, n_symbols)), axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def _persistent_momentum_panel(n: int = 800, n_symbols: int = 6, seed: int = 1) -> pd.DataFrame:
    # A persistent cross-sectional spread: symbol i has a fixed drift, so long-winners/short-losers
    # earns a steady positive return -> a genuine (if synthetic) momentum edge.
    rng = np.random.default_rng(seed)
    drifts = np.linspace(-0.0010, 0.0010, n_symbols)
    steps = rng.normal(0.0, 0.006, (n, n_symbols)) + drifts
    prices = 100.0 * np.cumprod(1.0 + steps, axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def test_search_produces_a_trial_per_strategy_and_a_gate_verdict() -> None:
    exp = run_cross_sectional_search(_noise_panel(), rationale="unit")
    assert isinstance(exp, CrossSectionalExperiment)
    assert {t.strategy_name for t in exp.trials} == {"xs_momentum", "xs_reversal"}
    assert exp.universe_symbols == [f"S{i}" for i in range(6)]
    assert exp.best_gate_result is not None
    assert exp.lifetime_trials > 0
    # graduate iff the gate passed (the gate is the single source of truth).
    assert (exp.graduate is not None) == exp.best_gate_result.passed


def test_a_working_factor_graduates_under_a_lenient_gate() -> None:
    exp = run_cross_sectional_search(
        _persistent_momentum_panel(), strategy_names=["xs_momentum"], config=_LENIENT
    )
    assert exp.best_gate_result is not None and exp.best_gate_result.passed
    assert exp.graduate is not None
    assert exp.graduate.strategy_name == "xs_momentum"
    assert "quantile" in exp.graduate.parameters  # the searched quantile is recorded
    assert exp.graduate.holdout_n_bars > 0


def test_value_strategy_is_searched_when_scores_are_supplied() -> None:
    scores = {f"S{i}": float(i) / 6.0 for i in range(6)}
    exp = run_cross_sectional_search(
        _noise_panel(), strategy_names=["xs_value"], value_scores=scores, config=_LENIENT
    )
    assert [t.strategy_name for t in exp.trials] == ["xs_value"]


def test_unknown_strategy_names_are_skipped() -> None:
    exp = run_cross_sectional_search(_noise_panel(), strategy_names=["xs_momentum", "bogus"])
    assert [t.strategy_name for t in exp.trials] == ["xs_momentum"]


def test_a_single_config_strategy_is_skipped_but_others_still_run() -> None:
    # One quantile -> xs_value has a single config (< 2) and is skipped for PBO; momentum survives.
    scores = {f"S{i}": float(i) for i in range(6)}
    exp = run_cross_sectional_search(
        _noise_panel(),
        strategy_names=["xs_momentum", "xs_value"],
        value_scores=scores,
        quantiles=(0.2,),
    )
    assert [t.strategy_name for t in exp.trials] == ["xs_momentum"]


def test_raises_when_no_strategy_has_enough_configs() -> None:
    with pytest.raises(ValueError, match="no valid cross-sectional"):
        run_cross_sectional_search(_noise_panel(), strategy_names=["bogus"])


def test_lifetime_trials_accumulates_prior_count() -> None:
    exp = run_cross_sectional_search(_noise_panel(), strategy_names=["xs_reversal"])
    baseline = exp.lifetime_trials
    with_prior = run_cross_sectional_search(
        _noise_panel(), strategy_names=["xs_reversal"], prior_trials=100
    )
    assert with_prior.lifetime_trials == baseline + 100


def test_experiment_is_json_serializable() -> None:
    exp = run_cross_sectional_search(_noise_panel(), strategy_names=["xs_momentum"])
    dumped = exp.model_dump(mode="json")
    assert dumped["strategy_names"] == ["xs_momentum"]
    assert "best_gate_result" in dumped
