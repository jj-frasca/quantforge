"""Experiment store (ADR-016 §5): the trial-counted research pool. Records every experiment —
ALL trials, not just winners — so findings compound and the lifetime trial count stays honest
for the DSR/MinTRL penalty. In-memory + JSON-file impls; DB is a later drop-in."""

from app.research.lab.experiment import (
    Experiment,
    Graduate,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    Trial,
)
from app.research.lab.gate import GateConfig, GateResult


def _trial(name: str, dsr: float) -> Trial:
    return Trial(
        strategy_name=name,
        parameters={"fast": 5, "slow": 20},
        observed_sharpe=1.2,
        deflated_sharpe=dsr,
        pbo=0.2,
        parameter_stability_score=0.7,
    )


def _experiment(symbol: str, n_trials: int, prior: int = 0, graduated: bool = False) -> Experiment:
    trials = [_trial(f"s{i}", 0.5 + i * 0.1) for i in range(n_trials)]
    graduate = None
    if graduated:
        graduate = Graduate(
            strategy_name="s0",
            parameters={"fast": 5, "slow": 20},
            gate_result=GateResult(
                passed=True,
                dsr_ok=True,
                pbo_ok=True,
                stability_ok=True,
                mintrl_ok=True,
                holdout_ok=True,
                required_track_record_years=9.2,
                gate_config_version="v",
            ),
            holdout_sharpe=0.8,
            holdout_total_return=0.15,
        )
    return Experiment(
        symbol=symbol,
        strategy_names=[t.strategy_name for t in trials],
        gate_config=GateConfig(),
        trials=trials,
        lifetime_trials=prior + n_trials,
        graduate=graduate,
        rationale="test run",
    )


def test_in_memory_store_adds_and_lists() -> None:
    store = InMemoryExperimentStore()
    exp = _experiment("AAPL", 3)
    store.add(exp)
    assert store.all() == [exp]


def test_trials_for_symbol_uses_max_cumulative_lifetime() -> None:
    # Real usage is cumulative: the 2nd AAPL run started with prior=3, so its lifetime_trials is 7.
    # trials_for_symbol returns the MAX cumulative count (prune-safe), not a sum of trial lists.
    store = InMemoryExperimentStore()
    store.add(_experiment("AAPL", 3))  # lifetime 3
    store.add(_experiment("AAPL", 4, prior=3))  # cumulative lifetime 7
    store.add(_experiment("MSFT", 5))
    assert store.trials_for_symbol("AAPL") == 7
    assert store.trials_for_symbol("MSFT") == 5
    assert store.trials_for_symbol("NVDA") == 0


def test_trials_for_symbol_survives_pruning_the_earlier_experiment() -> None:
    # Dropping the older experiment must NOT lower the MinTRL bar — the max cumulative count is
    # carried by the most-recent experiment, which pruning keeps (ADR-026 pool-size fix).
    store = InMemoryExperimentStore()
    store.add(_experiment("AAPL", 4, prior=3))  # only the recent (cumulative 7) experiment remains
    assert store.trials_for_symbol("AAPL") == 7


def test_json_file_store_persists_across_instances(tmp_path) -> None:
    path = tmp_path / "pool.json"
    writer = JsonFileExperimentStore(path)
    writer.add(_experiment("AAPL", 2, graduated=True))
    writer.add(_experiment("AAPL", 3, prior=2))  # cumulative lifetime 5

    # A brand-new instance on the same path sees the persisted experiments + counts.
    reader = JsonFileExperimentStore(path)
    assert len(reader.all()) == 2
    assert reader.trials_for_symbol("AAPL") == 5
    # The graduate (with its nested GateResult) round-trips losslessly.
    graduated = [e for e in reader.all() if e.graduate is not None]
    assert len(graduated) == 1
    assert graduated[0].graduate.gate_result.passed is True
    assert graduated[0].graduate.holdout_sharpe == 0.8


def test_json_file_store_starts_empty_when_file_absent(tmp_path) -> None:
    store = JsonFileExperimentStore(tmp_path / "does_not_exist.json")
    assert store.all() == []
    assert store.trials_for_symbol("AAPL") == 0
