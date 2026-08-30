"""Search orchestrator (ADR-014 Phase 2): propose candidates across catalog strategies ->
validate each on in-sample data -> pick the best -> score it on the sealed holdout -> apply the
graduation gate. Produces one Experiment with ALL trials recorded and the best candidate's
verdict (pass OR fail) attached."""

import json
import math

import numpy as np
import pandas as pd
import pytest

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import TRADING_DAYS, return_moments, sharpe_ratio
from app.research.fundamentals.distress import DistressScreen
from app.research.lab.experiment import Experiment, InMemoryExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.holdout import split_holdout
from app.research.lab.search import run_search
from app.research.strategies.builder import build_strategy_from_dict
from app.research.strategies.grid_generator import find_catalog_entry, grid_from_catalog
from app.validation.deflated_sharpe import probabilistic_sharpe_ratio
from app.validation.walk_forward import walk_forward_splits

_LENIENT = GateConfig(
    dsr_min=-100.0,
    pbo_max=1.01,
    stability_min=-1.0,
    holdout_sharpe_min=-100.0,
    require_beat_buy_and_hold=False,
)


def _snap(growth: float, net_margin: float) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol="AAPL",
        cik=320193,
        entity_name="Apple Inc.",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        revenue=400_000,
        revenue_growth_yoy=growth,
        net_margin=net_margin,
    )


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
    expected_configs = sum(
        len(grid_from_catalog(entry))
        for name in ("sma", "momentum")
        if (entry := find_catalog_entry(name)) is not None
    )
    assert expected_configs == 16
    assert exp.lifetime_trials == expected_configs
    assert sum(t.n_evaluated_configs for t in exp.trials) == expected_configs
    assert exp.best_strategy_name in {"sma", "momentum"}
    assert exp.best_gate_result is not None
    assert exp.rationale == "unit"


def test_prior_trials_feed_the_lifetime_count() -> None:
    exp = run_search(_random_walk_frame(1), "AAPL", ["sma", "momentum"], prior_trials=40)
    assert exp.lifetime_trials == 56  # 40 prior + 16 concrete configs this run


def test_prior_search_effort_increases_the_dsr_haircut() -> None:
    first = run_search(_random_walk_frame(1), "AAPL", ["sma", "momentum"])
    repeated = run_search(_random_walk_frame(1), "AAPL", ["sma", "momentum"], prior_trials=1_000)
    first_best = max(first.trials, key=lambda trial: trial.deflated_sharpe)
    repeated_best = max(repeated.trials, key=lambda trial: trial.deflated_sharpe)
    assert repeated_best.observed_sharpe == pytest.approx(first_best.observed_sharpe)
    assert repeated_best.deflated_sharpe < first_best.deflated_sharpe


def test_family_finalists_share_one_whole_search_dsr_haircut() -> None:
    exp = run_search(_random_walk_frame(8), "AAPL", ["sma", "momentum"])
    first, second = exp.trials
    assert first.observed_sharpe - first.deflated_sharpe == pytest.approx(
        second.observed_sharpe - second.deflated_sharpe
    )


def test_trial_budget_caps_concrete_configs_and_is_order_robust() -> None:
    gate = GateConfig(trial_budget=10)
    first = run_search(
        _random_walk_frame(8), "AAPL", ["sma", "momentum"], config=gate, refine=False
    )
    reordered = run_search(
        _random_walk_frame(8), "AAPL", ["momentum", "sma", "momentum"], config=gate, refine=False
    )

    assert first.lifetime_trials == sum(t.n_evaluated_configs for t in first.trials) == 10
    assert [
        (trial.strategy_name, trial.parameters, trial.n_evaluated_configs) for trial in first.trials
    ] == [
        (trial.strategy_name, trial.parameters, trial.n_evaluated_configs)
        for trial in reordered.trials
    ]
    assert first.best_strategy_name == reordered.best_strategy_name


def test_refinement_reserve_keeps_both_search_stages_inside_trial_budget() -> None:
    exp = run_search(
        _random_walk_frame(8),
        "AAPL",
        ["sma", "momentum"],
        config=GateConfig(trial_budget=12),
        refine=True,
    )

    assert exp.lifetime_trials == sum(t.n_evaluated_configs for t in exp.trials)
    assert exp.lifetime_trials <= 12


def test_trial_budget_too_small_for_requested_families_fails_loudly() -> None:
    with pytest.raises(ValueError, match="at least 4"):
        run_search(
            _random_walk_frame(8),
            "AAPL",
            ["sma", "momentum"],
            config=GateConfig(trial_budget=3),
        )


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
        dsr_min=-100.0,
        pbo_max=1.01,
        stability_min=-1.0,
        holdout_sharpe_min=-100.0,
        require_beat_buy_and_hold=False,
    )
    exp = run_search(_strong_uptrend_frame(0), "AAPL", ["sma", "momentum"], config=lenient)
    assert exp.best_gate_result is not None and exp.best_gate_result.passed is True
    assert exp.graduate is not None
    assert exp.graduate.strategy_name == exp.best_strategy_name
    assert isinstance(exp.graduate.holdout_sharpe, float)


def test_bad_fundamentals_veto_graduation_even_when_technicals_pass() -> None:
    # Lenient gate over a strong trend would graduate on technicals — but collapsing revenue
    # vetoes it (ADR-017). The failed screen is recorded with reasons.
    exp = run_search(
        _strong_uptrend_frame(0),
        "AAPL",
        ["sma", "momentum"],
        config=_LENIENT,
        fundamentals=_snap(growth=-0.30, net_margin=-0.05),
        fundamental_criteria=FundamentalCriteria(),
    )
    assert exp.best_gate_result is not None and exp.best_gate_result.passed is True
    assert exp.graduate is None  # vetoed
    assert exp.fundamental_screen is not None and exp.fundamental_screen.passed is False
    assert exp.fundamentals is not None and exp.fundamentals.cik == 320193


def test_healthy_fundamentals_allow_graduation() -> None:
    exp = run_search(
        _strong_uptrend_frame(0),
        "AAPL",
        ["sma", "momentum"],
        config=_LENIENT,
        fundamentals=_snap(growth=0.15, net_margin=0.25),
        fundamental_criteria=FundamentalCriteria(),
    )
    assert exp.fundamental_screen is not None and exp.fundamental_screen.passed is True
    assert exp.graduate is not None


def test_distress_vetoes_graduation_even_when_technicals_pass() -> None:
    # A lenient gate over a strong trend would graduate on technicals — but a hard financial-distress
    # screen blocks it (ADR-029 3c), a business-quality rail on top of the statistical gate.
    exp = run_search(
        _strong_uptrend_frame(0),
        "AAPL",
        ["sma", "momentum"],
        config=_LENIENT,
        distress_screen=DistressScreen(distressed=True, reasons=["negative net income"]),
    )
    assert exp.best_gate_result is not None and exp.best_gate_result.passed is True
    assert exp.graduate is None  # vetoed by distress despite lenient technicals
    assert exp.distress_screen is not None and exp.distress_screen.distressed is True


def test_non_distressed_screen_allows_graduation() -> None:
    exp = run_search(
        _strong_uptrend_frame(0),
        "AAPL",
        ["sma", "momentum"],
        config=_LENIENT,
        distress_screen=DistressScreen(distressed=False, reasons=[]),
    )
    assert exp.graduate is not None
    assert exp.distress_screen is not None and exp.distress_screen.distressed is False


def test_refine_adds_a_trial_and_raises_the_bar() -> None:
    # Coarse-to-fine: the refined family summary represents every concrete refined config.
    base = run_search(_random_walk_frame(0), "AAPL", ["sma", "momentum"])
    refined = run_search(_random_walk_frame(0), "AAPL", ["sma", "momentum"], refine=True)
    assert len(refined.trials) == len(base.trials) + 1
    assert refined.lifetime_trials == sum(t.n_evaluated_configs for t in refined.trials)
    assert refined.lifetime_trials > base.lifetime_trials + 1
    assert refined.best_gate_result is not None


def test_experiment_records_into_the_pool_and_counts_trials() -> None:
    store = InMemoryExperimentStore()
    exp = run_search(_random_walk_frame(5), "AAPL", ["sma", "momentum"], config=GateConfig())
    store.add(exp)
    assert store.trials_for_symbol("AAPL") == exp.lifetime_trials == 16


def test_every_trial_records_its_walk_forward_estimate() -> None:
    """ADR-038: the walk-forward number reaches the research pool, not just the report."""
    exp = run_search(_random_walk_frame(2), "AAPL", ["sma", "momentum"], refine=True)
    assert len(exp.trials) == 3  # 2 coarse + 1 refined
    assert all(t.walk_forward_oos_sharpe is not None for t in exp.trials)
    assert all(np.isfinite(t.walk_forward_oos_sharpe or 0.0) for t in exp.trials)


def test_walk_forward_estimate_is_independent_of_the_holdout_sharpe() -> None:
    """It is a second, prequential out-of-sample view — not a restatement of the locked holdout."""
    # Use the strong edge fixture so the now-honest 16-config MinTRL denominator still graduates;
    # the assertion is about the two OOS measurements, not whether random noise clears MinTRL.
    exp = run_search(_strong_uptrend_frame(3), "AAPL", ["sma", "momentum"], config=_LENIENT)
    assert exp.graduate is not None
    best = max(exp.trials, key=lambda t: t.deflated_sharpe)
    assert best.walk_forward_oos_sharpe != exp.graduate.holdout_sharpe


def test_every_trial_records_its_purged_cv_estimate() -> None:
    """ADR-039: the purged-CV number reaches the pool alongside the walk-forward one."""
    exp = run_search(_random_walk_frame(4), "AAPL", ["sma", "momentum"], refine=True)
    assert all(t.purged_cv_oos_sharpe is not None for t in exp.trials)


def test_purged_cv_and_walk_forward_are_recorded_separately() -> None:
    """They answer different questions; collapsing them into one number would hide the gap."""
    exp = run_search(_random_walk_frame(5), "AAPL", ["sma", "momentum"])
    best = max(exp.trials, key=lambda t: t.deflated_sharpe)
    assert best.purged_cv_oos_sharpe != best.walk_forward_oos_sharpe


# --- ADR-052: an experiment must name the search family that produced it ---


def test_search_records_the_resolved_hypothesis_family() -> None:
    """The pool's every comparison against a calibration artifact is a claim that both sides
    resolved the same family. Before this, establishing that meant diffing commit timestamps
    against workflow start times."""
    from app.research.lab.calibration import calibration_search_version

    config = GateConfig()
    exp = run_search(_random_walk_frame(11), "AAPL", ["sma", "momentum"], config=config)

    assert exp.search_config_version == calibration_search_version(
        ["sma", "momentum"], n_per_param=3, config=config, refine=False
    )


def test_a_search_over_a_different_family_records_a_different_version() -> None:
    frame = _random_walk_frame(12)
    narrow = run_search(frame, "AAPL", ["sma"])
    wide = run_search(frame, "AAPL", ["sma", "momentum"])

    assert narrow.search_config_version != wide.search_config_version


def test_refinement_changes_the_recorded_family() -> None:
    """Production refines and the null calibration refines; a coarse-only run is a different
    procedure and must not compare equal to either (ADR-047)."""
    frame = _random_walk_frame(13)
    coarse = run_search(frame, "AAPL", ["sma"], refine=False)
    refined = run_search(frame, "AAPL", ["sma"], refine=True)

    assert coarse.search_config_version != refined.search_config_version


def test_an_experiment_written_before_this_field_reads_back_as_unspecified() -> None:
    """The 3,237 rows already in the pool cannot have their family reconstructed. A synthesized
    value would be indistinguishable from a measured one."""
    exp = run_search(_random_walk_frame(14), "AAPL", ["sma"])
    legacy = Experiment.model_validate_json(exp.model_dump_json(exclude={"search_config_version"}))

    assert legacy.search_config_version == "legacy-unspecified"


def test_search_records_the_history_it_searched() -> None:
    """ADR-051's comparison lists the real side's unknown history length as a limitation: only
    Graduate carried a bar count, and the run that produced the result graduated nothing."""
    frame = _random_walk_frame(15)
    exp = run_search(frame, "AAPL", ["sma"])

    assert exp.n_bars == len(frame)


def test_an_experiment_written_before_the_bar_count_reads_back_as_unknown() -> None:
    exp = run_search(_random_walk_frame(16), "AAPL", ["sma"])
    legacy = Experiment.model_validate_json(exp.model_dump_json(exclude={"n_bars"}))

    assert legacy.n_bars is None


def test_every_trial_records_the_paper_deflated_sharpe_probability() -> None:
    """ADR-054 decision 3: both statistics now ride on every trial, so their disagreement is
    measurable rather than hypothetical."""
    exp = run_search(_random_walk_frame(17), "AAPL", ["sma", "momentum"], refine=True)

    assert len(exp.trials) == 3  # 2 coarse + 1 refined
    for trial in exp.trials:
        assert trial.deflated_sharpe_probability is not None
        assert 0.0 <= trial.deflated_sharpe_probability <= 1.0


def test_the_recorded_probability_is_priced_per_period_not_annualized() -> None:
    """The margin is in ANNUALIZED Sharpe units; the PSR is a function of the PER-PERIOD Sharpe
    and the per-period moments together. Rebuilding the finalist and reconstructing the haircut
    from the stored margin pins the recorded probability end to end — an annualized Sharpe against
    per-period moments would saturate this to 0.0 or 1.0."""
    frame = _random_walk_frame(18)
    exp = run_search(frame, "AAPL", ["sma"])
    trial = exp.trials[0]
    handle, _ = split_holdout(frame, "AAPL")
    finalist = build_strategy_from_dict(trial.strategy_name, trial.parameters)
    moments = return_moments(BacktestEngine().run_strategy(handle.frame, finalist).returns)
    assert moments is not None

    scale = math.sqrt(TRADING_DAYS)
    expected = probabilistic_sharpe_ratio(
        trial.observed_sharpe / scale,
        benchmark_sr=(trial.observed_sharpe - trial.deflated_sharpe) / scale,
        n_returns=moments.n_returns,
        skew=moments.skew,
        kurtosis=moments.kurtosis,
    )
    assert trial.deflated_sharpe_probability == pytest.approx(expected)


def test_a_trial_written_before_the_probability_reads_back_as_unmeasured() -> None:
    """The 3,237 committed pool rows predate the field. None means "not measured", while a 0.0
    would read as a track record the paper's test rejects outright."""
    exp = run_search(_random_walk_frame(19), "AAPL", ["sma"])
    payload = json.loads(exp.model_dump_json())
    for row in payload["trials"]:
        del row["deflated_sharpe_probability"]

    legacy = Experiment.model_validate(payload)

    assert all(t.deflated_sharpe_probability is None for t in legacy.trials)


def test_the_probability_prices_the_whole_search_effort() -> None:
    """It must use the same lifetime denominator the margin does: prior effort lowers it."""
    frame = _random_walk_frame(20)
    fresh = run_search(frame, "AAPL", ["sma", "momentum"])
    repeated = run_search(frame, "AAPL", ["sma", "momentum"], prior_trials=50_000)

    for before, after in zip(fresh.trials, repeated.trials, strict=True):
        assert before.deflated_sharpe_probability is not None
        assert after.deflated_sharpe_probability is not None
        assert after.deflated_sharpe_probability < before.deflated_sharpe_probability


# --- ADR-068: what holding the same window earned, recorded beside what the search earned ---


def test_the_experiment_records_the_hold_sharpe_of_its_own_search_window() -> None:
    frame = _random_walk_frame(31)
    exp = run_search(frame, "AAPL", ["sma", "momentum"], rationale="unit")

    handle, _ = split_holdout(frame, "AAPL")
    hold = handle.frame["close"].pct_change().fillna(0.0).to_numpy(dtype=float)
    splits = walk_forward_splits(len(handle.frame), 5)
    expected = float(np.mean([sharpe_ratio(pd.Series(hold[test_idx])) for _, test_idx in splits]))

    assert exp.walk_forward_hold_sharpe == pytest.approx(expected)


def test_the_hold_sharpe_excludes_the_sealed_holdout() -> None:
    """It benchmarks the walk-forward windows, which never touch the sealed split (ADR-016)."""
    frame = _random_walk_frame(32)
    exp = run_search(frame, "AAPL", ["sma", "momentum"], rationale="unit")

    whole = frame["close"].pct_change().fillna(0.0).to_numpy(dtype=float)
    splits = walk_forward_splits(len(frame), 5)
    whole_window = float(
        np.mean([sharpe_ratio(pd.Series(whole[test_idx])) for _, test_idx in splits])
    )

    assert exp.walk_forward_hold_sharpe is not None
    assert exp.walk_forward_hold_sharpe != pytest.approx(whole_window)


def test_an_experiment_written_before_the_benchmark_reads_as_not_measured() -> None:
    """ADR-067: the pool predates the field and must not report an excess of zero."""
    assert (
        Experiment(
            symbol="AAPL",
            strategy_names=["sma"],
            gate_config=GateConfig(),
            trials=[],
            lifetime_trials=0,
        ).walk_forward_hold_sharpe
        is None
    )
