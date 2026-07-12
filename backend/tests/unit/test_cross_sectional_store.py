"""Persistent store for cross-sectional experiments (ADR-024 integration). The per-strategy/
universe analog of JsonFileExperimentStore: a run's effort compounds via `prior_trials` (the
cumulative trial count feeds the next search's MinTRL bar), and findings survive in a JSON file."""

from pathlib import Path

from app.research.cross_sectional.search import CrossSectionalExperiment
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.lab.gate import GateConfig


def _exp(lifetime_trials: int) -> CrossSectionalExperiment:
    return CrossSectionalExperiment(
        universe_symbols=["A", "B"],
        strategy_names=["xs_momentum"],
        gate_config=GateConfig(),
        trials=[],
        lifetime_trials=lifetime_trials,
    )


def test_in_memory_store_adds_and_lists() -> None:
    store = InMemoryCrossSectionalStore()
    store.add(_exp(10))
    store.add(_exp(25))
    assert [e.lifetime_trials for e in store.all()] == [10, 25]


def test_prior_trials_is_zero_when_empty() -> None:
    assert InMemoryCrossSectionalStore().prior_trials() == 0


def test_prior_trials_is_the_running_cumulative_total() -> None:
    # lifetime_trials is cumulative when runs chain through the store, so the max is the total.
    store = InMemoryCrossSectionalStore()
    store.add(_exp(18))
    store.add(_exp(36))
    assert store.prior_trials() == 36


def test_json_store_round_trips_through_the_file(tmp_path: Path) -> None:
    path = tmp_path / "xs_pool.json"
    store = JsonFileCrossSectionalStore(path)
    store.add(_exp(18))
    store.add(_exp(36))

    reloaded = JsonFileCrossSectionalStore(path)
    assert [e.lifetime_trials for e in reloaded.all()] == [18, 36]
    assert reloaded.prior_trials() == 36
    assert path.read_text().endswith("\n")  # trailing newline satisfies end-of-file-fixer


def test_json_store_is_empty_before_first_write(tmp_path: Path) -> None:
    store = JsonFileCrossSectionalStore(tmp_path / "absent.json")
    assert store.all() == []
    assert store.prior_trials() == 0
