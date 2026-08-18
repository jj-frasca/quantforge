"""Pool merge (ADR-026): the consolidation job folds every shard's experiments into the research
pool, deduping by experiment_id so a re-run of a shard is idempotent (no duplicate rows)."""

from datetime import UTC, datetime
from uuid import uuid4

from app.research.lab.experiment import Experiment, Graduate, InMemoryExperimentStore, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.pool_merge import merge_experiments, prune_pool


def _exp(symbol: str) -> Experiment:
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[],
        lifetime_trials=0,
    )


def _dated(symbol: str, day: int, *, lifetime: int = 1, graduated: bool = False) -> Experiment:
    trial = Trial(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    graduate = None
    if graduated:
        gr = GateResult(
            passed=True,
            dsr_ok=True,
            pbo_ok=True,
            stability_ok=True,
            mintrl_ok=True,
            holdout_ok=True,
            required_track_record_years=1.0,
            gate_config_version="v",
        )
        graduate = Graduate(
            strategy_name="sma",
            parameters={"fast": 5, "slow": 20},
            gate_result=gr,
            holdout_sharpe=1.0,
            holdout_total_return=0.1,
            holdout_n_bars=252,
        )
    return Experiment(
        symbol=symbol,
        created_at=datetime(2026, 1, day, tzinfo=UTC),
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[trial],
        lifetime_trials=lifetime,
        graduate=graduate,
    )


def test_prune_keeps_all_graduates() -> None:
    grads = [_dated("A", d, graduated=True) for d in range(1, 6)]
    pruned = prune_pool(grads, keep_non_graduate_per_symbol=0)
    assert len(pruned) == 5  # every graduate survives even with 0 non-grads kept


def test_prune_keeps_only_recent_non_graduates_per_symbol() -> None:
    exps = [_dated("A", d) for d in range(1, 11)]  # 10 non-graduate A experiments, days 1..10
    pruned = prune_pool(exps, keep_non_graduate_per_symbol=3)
    a = [e for e in pruned if e.symbol == "A"]
    assert len(a) == 3
    assert {e.created_at.day for e in a} == {8, 9, 10}  # the 3 most recent


def test_prune_preserves_the_mintrl_trial_count() -> None:
    # The most-recent experiment carries the max cumulative lifetime_trials; pruning keeps it, so
    # trials_for_symbol is unchanged after pruning (honesty preserved).
    exps = [_dated("A", d, lifetime=d * 10) for d in range(1, 11)]  # lifetime grows with recency
    before = InMemoryExperimentStore()
    for e in exps:
        before.add(e)
    pruned = prune_pool(exps, keep_non_graduate_per_symbol=2)
    after = InMemoryExperimentStore()
    for e in pruned:
        after.add(e)
    assert before.trials_for_symbol("A") == after.trials_for_symbol("A") == 100


def test_merges_disjoint_experiments() -> None:
    a, b = _exp("AAA"), _exp("BBB")
    merged = merge_experiments([a], [b])
    assert {e.symbol for e in merged} == {"AAA", "BBB"}


def test_dedups_by_experiment_id() -> None:
    a = _exp("AAA")
    same_id = a.model_copy(update={"symbol": "AAA-updated"})  # same experiment_id
    merged = merge_experiments([a], [same_id])
    assert len(merged) == 1
    assert merged[0].symbol == "AAA-updated"  # incoming wins on collision (idempotent re-run)


def test_preserves_existing_and_appends_new() -> None:
    existing = [_exp("AAA"), _exp("BBB")]
    incoming = [_exp("CCC")]
    merged = merge_experiments(existing, incoming)
    assert [e.symbol for e in merged] == ["AAA", "BBB", "CCC"]


def test_empty_inputs() -> None:
    assert merge_experiments([], []) == []
    one = _exp("AAA")
    assert [e.experiment_id for e in merge_experiments([one], [])] == [one.experiment_id]
    assert [e.experiment_id for e in merge_experiments([], [one])] == [one.experiment_id]


def test_dedups_within_and_across_batches() -> None:
    shared_id = uuid4()
    a = _exp("A").model_copy(update={"experiment_id": shared_id})
    b = _exp("B").model_copy(update={"experiment_id": shared_id})
    merged = merge_experiments([a], [b])
    assert len(merged) == 1 and merged[0].symbol == "B"
