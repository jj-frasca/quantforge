"""Search orchestrator (ADR-014 Phase 2): propose candidates across catalog strategies ->
validate each on in-sample data -> pick the best -> score it on the sealed holdout -> apply the
graduation gate. Produces one Experiment with ALL trials recorded and the best candidate's
verdict (pass OR fail) attached."""

import numpy as np
import pandas as pd
import pytest

from app.research.lab.experiment import Experiment, InMemoryExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.search import run_search


def _random_walk_frame(seed: int, n: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(0.0003, 0.02, n))
    index = pd.date_range("2016-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=index)


def test_run_search_produces_an_experiment_with_a_trial_per_strategy() -> None:
    exp = run_search(_random_walk_frame(0), "AAPL", ["sma", "momentum"], rationale="unit")
    assert isinstance(exp, Experiment)
    assert exp.symbol == "AAPL"
    assert len(exp.trials) == 2
    assert exp.lifetime_trials == 2
    assert exp.best_strategy_name in {"sma", "momentum"}
    assert exp.best_gate_result is not None
    assert exp.rationale == "unit"


def test_prior_trials_feed_the_lifetime_count() -> None:
    exp = run_search(_random_walk_frame(1), "AAPL", ["sma", "momentum"], prior_trials=40)
    assert exp.lifetime_trials == 42  # 40 prior + 2 this run


def test_search_rejects_an_empty_strategy_set() -> None:
    with pytest.raises(ValueError):
        run_search(_random_walk_frame(2), "AAPL", [])


def test_search_skips_unknown_strategy_names() -> None:
    exp = run_search(_random_walk_frame(3), "AAPL", ["sma", "not_a_strategy"])
    assert exp.strategy_names == ["sma"]
    assert len(exp.trials) == 1


def test_huge_trial_count_fails_mintrl_and_blocks_graduation() -> None:
    # The honesty flywheel: after a million lifetime trials, no ~9-year sample can justify any
    # Sharpe -> MinTRL fails -> nothing graduates, regardless of in-sample metrics.
    exp = run_search(_random_walk_frame(4), "AAPL", ["sma", "momentum"], prior_trials=1_000_000)
    assert exp.best_gate_result is not None
    assert exp.best_gate_result.mintrl_ok is False
    assert exp.graduate is None


def _strong_uptrend_frame(seed: int, n: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(0.0010, 0.008, n))  # high drift, low vol
    index = pd.date_range("2016-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=index)


def test_strategy_with_too_few_grid_configs_is_skipped() -> None:
    # n_per_param=1 collapses each param to a single value -> < 2 configs -> can't run PBO ->
    # the strategy is skipped; with only that one requested, the search has nothing to run.
    with pytest.raises(ValueError):
        run_search(_random_walk_frame(6), "AAPL", ["sma"], n_per_param=1)


def test_a_passing_gate_records_a_graduate() -> None:
    # A permissive GateConfig over a strong-trend series lets a candidate clear the gate, so the
    # graduate (with its holdout score) is recorded. Exercises the graduation branch.
    lenient = GateConfig(
        dsr_min=-100.0, pbo_max=1.01, stability_min=-1.0, holdout_sharpe_min=-100.0
    )
    exp = run_search(_strong_uptrend_frame(0), "AAPL", ["sma", "momentum"], config=lenient)
    assert exp.best_gate_result is not None and exp.best_gate_result.passed is True
    assert exp.graduate is not None
    assert exp.graduate.strategy_name == exp.best_strategy_name
    assert isinstance(exp.graduate.holdout_sharpe, float)


def test_experiment_records_into_the_pool_and_counts_trials() -> None:
    store = InMemoryExperimentStore()
    exp = run_search(_random_walk_frame(5), "AAPL", ["sma", "momentum"], config=GateConfig())
    store.add(exp)
    assert store.trials_for_symbol("AAPL") == 2
