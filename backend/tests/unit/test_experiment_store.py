"""Experiment store (ADR-016 §5): the trial-counted research pool. Records every experiment —
ALL trials, not just winners — so findings compound and the lifetime trial count stays honest
for the DSR/MinTRL penalty. In-memory + JSON-file impls; DB is a later drop-in."""

import pytest

from app.research.lab.experiment import (
    Experiment,
    Graduate,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    PriorAwareExperimentStore,
    Trial,
    migrate_pool_to_partitions,
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


# ---- PartitionedExperimentStore (ADR-032) --------------------------------------------------------


def test_partitioned_store_writes_one_file_per_symbol(tmp_path) -> None:
    store = PartitionedExperimentStore(tmp_path / "research_pool")
    store.add(_experiment("AAPL", 2))
    store.add(_experiment("AAPL", 3, prior=2))
    store.add(_experiment("MSFT", 4))
    written = sorted(p.name for p in (tmp_path / "research_pool").glob("*.json"))
    assert written == ["AAPL.json", "MSFT.json"]


def test_partitioned_store_persists_across_instances(tmp_path) -> None:
    path = tmp_path / "research_pool"
    writer = PartitionedExperimentStore(path)
    writer.add(_experiment("AAPL", 2, graduated=True))
    writer.add(_experiment("AAPL", 3, prior=2))  # cumulative lifetime 5

    reader = PartitionedExperimentStore(path)
    assert len(reader.all()) == 2
    assert reader.trials_for_symbol("AAPL") == 5
    graduated = [e for e in reader.all() if e.graduate is not None]
    assert len(graduated) == 1
    assert graduated[0].graduate.gate_result.passed is True


def test_partitioned_store_starts_empty_when_the_directory_is_absent(tmp_path) -> None:
    store = PartitionedExperimentStore(tmp_path / "never_created")
    assert store.all() == []
    assert store.trials_for_symbol("AAPL") == 0


def test_partitioned_store_reads_only_the_requested_symbols_partition(tmp_path) -> None:
    # The hot path in every hunt. A corrupt partition for an unrelated symbol must not break the
    # lookup — that is the whole point of not parsing the entire 45 MB pool to count one symbol.
    path = tmp_path / "research_pool"
    store = PartitionedExperimentStore(path)
    store.add(_experiment("AAPL", 4, prior=3))
    (path / "BROKEN.json").write_text("{ not json")
    assert store.trials_for_symbol("AAPL") == 7


def test_partitioned_store_all_is_sorted_by_symbol_for_deterministic_output(tmp_path) -> None:
    store = PartitionedExperimentStore(tmp_path / "research_pool")
    for symbol in ("MSFT", "AAPL", "NVDA"):
        store.add(_experiment(symbol, 2))
    assert [e.symbol for e in store.all()] == ["AAPL", "MSFT", "NVDA"]


def test_partitioned_store_sanitizes_a_symbol_that_could_escape_the_directory(tmp_path) -> None:
    path = tmp_path / "research_pool"
    store = PartitionedExperimentStore(path)
    store.add(_experiment("../../etc/passwd", 1))
    assert [p.name for p in path.glob("*.json")] == [".._.._ETC_PASSWD.json"]
    assert not (tmp_path.parent / "etc").exists()


def test_partitioned_store_keeps_real_ticker_punctuation(tmp_path) -> None:
    # BRK-B, BF.B and ^GSPC are legitimate symbols in the universes — they must not be mangled.
    path = tmp_path / "research_pool"
    store = PartitionedExperimentStore(path)
    for symbol in ("BRK-B", "BF.B", "^GSPC"):
        store.add(_experiment(symbol, 1))
    assert sorted(p.stem for p in path.glob("*.json")) == ["BF.B", "BRK-B", "^GSPC"]


# ---- migrate_pool_to_partitions (ADR-032 one-shot migration) -------------------------------------


def test_migration_splits_the_monolith_and_removes_it(tmp_path) -> None:
    source = tmp_path / "research_pool.json"
    monolith = JsonFileExperimentStore(source)
    for symbol in ("AAPL", "AAPL", "MSFT"):
        monolith.add(_experiment(symbol, 3))
    original = {e.experiment_id for e in monolith.all()}

    directory = tmp_path / "research_pool"
    assert migrate_pool_to_partitions(source, directory) == 3
    assert not source.exists()  # removed only AFTER the partitions verified
    migrated = PartitionedExperimentStore(directory)
    assert {e.experiment_id for e in migrated.all()} == original
    assert sorted(p.name for p in directory.glob("*.json")) == ["AAPL.json", "MSFT.json"]


def test_migration_is_a_noop_when_there_is_nothing_to_migrate(tmp_path) -> None:
    directory = tmp_path / "research_pool"
    assert migrate_pool_to_partitions(tmp_path / "absent.json", directory) == 0
    assert not directory.exists()


def test_migration_refuses_a_non_empty_destination(tmp_path) -> None:
    # Re-running the migration must not silently duplicate the whole scientific record.
    source = tmp_path / "research_pool.json"
    JsonFileExperimentStore(source).add(_experiment("AAPL", 3))
    directory = tmp_path / "research_pool"
    PartitionedExperimentStore(directory).add(_experiment("MSFT", 2))

    with pytest.raises(RuntimeError, match="not empty"):
        migrate_pool_to_partitions(source, directory)
    assert source.exists()  # the source is left intact for a human to reconcile


def test_partitioned_store_bounds_a_symbols_partition_to_the_recent_non_graduates(tmp_path) -> None:
    # ADR-032 + ADR-026: unbounded growth is what pushed the pool past GitHub's 100 MB wall.
    # Retention is per-symbol now, and applied by the STORE so every writer is bounded — not only
    # the consolidate script that happened to remember to call prune_pool.
    store = PartitionedExperimentStore(tmp_path / "research_pool", keep_non_graduate_per_symbol=3)
    for i in range(8):
        store.add(_experiment("AAPL", 2, prior=i))
    store.add(_experiment("AAPL", 2, prior=99, graduated=True))
    kept = store.all()
    assert len(kept) == 4  # 3 most-recent non-graduates + the graduate
    assert sum(1 for e in kept if e.graduate is not None) == 1


def test_partitioned_store_retention_never_lowers_the_mintrl_bar(tmp_path) -> None:
    # The dropped experiments carried smaller cumulative counts; the most-recent one carries the
    # max and is always kept, so the graduation bar is unchanged by retention.
    store = PartitionedExperimentStore(tmp_path / "research_pool", keep_non_graduate_per_symbol=2)
    for prior in (0, 10, 20, 30):
        store.add(_experiment("AAPL", 5, prior=prior))
    assert store.trials_for_symbol("AAPL") == 35


def test_partitioned_store_extend_is_idempotent_on_experiment_id(tmp_path) -> None:
    # Re-running a shard must replace its experiments, never duplicate the record.
    store = PartitionedExperimentStore(tmp_path / "research_pool")
    batch = [_experiment("AAPL", 2), _experiment("MSFT", 3)]
    store.extend(batch)
    store.extend(batch)
    assert {e.experiment_id for e in store.all()} == {e.experiment_id for e in batch}
    assert len(store.all()) == 2


def test_migration_refuses_to_lose_experiments_to_retention(tmp_path) -> None:
    # Retention is disabled during the move by default. If a caller forces a limit that would drop
    # rows, the verification must fail and leave the monolith untouched — a migration that silently
    # loses part of the scientific record is a bug.
    source = tmp_path / "research_pool.json"
    monolith = JsonFileExperimentStore(source)
    for prior in range(6):
        monolith.add(_experiment("AAPL", 2, prior=prior))

    with pytest.raises(RuntimeError, match="does not match"):
        migrate_pool_to_partitions(
            source, tmp_path / "research_pool", keep_non_graduate_per_symbol=2
        )
    assert source.exists()


def test_migration_keeps_every_experiment_for_a_heavily_hunted_symbol(tmp_path) -> None:
    source = tmp_path / "research_pool.json"
    monolith = JsonFileExperimentStore(source)
    for prior in range(20):
        monolith.add(_experiment("AAPL", 2, prior=prior))

    directory = tmp_path / "research_pool"
    assert migrate_pool_to_partitions(source, directory) == 20
    assert len(PartitionedExperimentStore(directory).all()) == 20


def test_prior_aware_store_counts_trials_from_the_pool_it_is_adding_to(tmp_path) -> None:
    # ADR-062: a shard writes its own file but must price the selection breadth already recorded in
    # the committed pool. Without this the DSR/MinTRL denominator resets to zero on every run.
    prior = PartitionedExperimentStore(tmp_path / "research_pool")
    prior.add(_experiment("AAPL", 5, prior=135))
    shard = JsonFileExperimentStore(tmp_path / "shard_0.json")
    store = PriorAwareExperimentStore(writer=shard, prior=prior)

    assert store.trials_for_symbol("AAPL") == 140
    assert store.trials_for_symbol("MSFT") == 0


def test_prior_aware_store_takes_the_max_so_a_fresh_shard_never_lowers_the_bar(tmp_path) -> None:
    prior = PartitionedExperimentStore(tmp_path / "research_pool")
    prior.add(_experiment("AAPL", 5, prior=135))
    shard = JsonFileExperimentStore(tmp_path / "shard_0.json")
    store = PriorAwareExperimentStore(writer=shard, prior=prior)
    store.add(_experiment("AAPL", 5, prior=0))  # this run alone, as the shard file records it

    assert store.trials_for_symbol("AAPL") == 140


def test_prior_aware_store_writes_only_to_the_writer(tmp_path) -> None:
    # ADR-030's single-writer rule and ADR-026's race-free consolidation both depend on this: ten
    # parallel shards read the same pool directory and none of them may write it.
    prior = PartitionedExperimentStore(tmp_path / "research_pool")
    prior.add(_experiment("AAPL", 5, prior=135))
    shard = JsonFileExperimentStore(tmp_path / "shard_0.json")
    store = PriorAwareExperimentStore(writer=shard, prior=prior)
    added = _experiment("MSFT", 3)
    store.add(added)

    assert [e.experiment_id for e in shard.all()] == [added.experiment_id]
    assert [e.symbol for e in prior.all()] == ["AAPL"]
    assert [e.experiment_id for e in store.all()] == [added.experiment_id]
