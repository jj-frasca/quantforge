"""Pool merge (ADR-026): the consolidation job folds every shard's experiments into the research
pool, deduping by experiment_id so a re-run of a shard is idempotent (no duplicate rows)."""

from uuid import uuid4

from app.research.lab.experiment import Experiment
from app.research.lab.gate import GateConfig
from app.research.lab.pool_merge import merge_experiments


def _exp(symbol: str) -> Experiment:
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[],
        lifetime_trials=0,
    )


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
