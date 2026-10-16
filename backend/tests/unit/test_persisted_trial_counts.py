"""ADR-299: recorded candidate evidence bounds the lifetime count carried into the next hunt."""

import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.lab.experiment import (
    Experiment,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    Trial,
)
from app.research.lab.gate import GateConfig

INVALID_TYPES = [
    True,
    False,
    np.bool_(True),
    1.0,
    1.5,
    np.float64(1),
    Fraction(1),
    Fraction(3, 2),
    Decimal(1),
    "1",
    None,
    [],
    np.array(1),
]


def trial(kind: str, count: Any = 4, name: str = "manual") -> Any:
    cls = Trial if kind == "longitudinal" else CrossSectionalTrial
    payload = {
        "strategy_name": name,
        "parameters": {},
        "observed_sharpe": 1.0,
        "deflated_sharpe": 0.5,
        "pbo": 0.1,
        "parameter_stability_score": 0.8,
    }
    if count is not None:
        payload["n_evaluated_configs"] = count
    return cls(**payload)


def experiment(kind: str, lifetime: Any = 4, counts: tuple[Any, ...] = (4,)) -> Any:
    trials = [trial(kind, count, f"s{i}") for i, count in enumerate(counts)]
    payload = {
        "strategy_names": [t.strategy_name for t in trials],
        "gate_config": GateConfig(),
        "trials": trials,
        "lifetime_trials": lifetime,
    }
    if kind == "longitudinal":
        return Experiment(symbol="MANUAL", **payload)
    return CrossSectionalExperiment(universe_symbols=["A", "B"], **payload)


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
@pytest.mark.parametrize("count", [*INVALID_TYPES, 0, -1])
def test_trial_original_evaluated_count_rejects_coercion_and_invalid_domain(
    kind: str, count: Any
) -> None:
    # None means an omitted legacy field in the factory; explicit null is tested below.
    if count is None:
        payload = trial(kind).model_dump(round_trip=True)
        payload["n_evaluated_configs"] = None
        with pytest.raises(ValueError, match="n_evaluated_configs"):
            type(trial(kind)).model_validate(payload)
    else:
        with pytest.raises(ValueError, match="n_evaluated_configs"):
            trial(kind, count)


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
@pytest.mark.parametrize("count", [*INVALID_TYPES, -1])
def test_experiment_original_lifetime_rejects_coercion_even_without_trials(
    kind: str, count: Any
) -> None:
    with pytest.raises(ValueError, match="lifetime_trials"):
        experiment(kind, count, ())


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
@pytest.mark.parametrize("counts", [(4,), (2, 3), (None, None)])
@pytest.mark.parametrize("through_json", [False, True])
def test_experiment_lifetime_cannot_understate_its_recorded_candidate_lower_bound(
    kind: str, counts: tuple[Any, ...], through_json: bool
) -> None:
    total = sum(1 if value is None else value for value in counts)
    good = experiment(kind, total, counts)
    payload = good.model_dump(mode="json")
    payload["lifetime_trials"] = total - 1
    for item, count in zip(payload["trials"], counts, strict=True):
        if count is None:
            item.pop("n_evaluated_configs")
    with pytest.raises(ValueError, match="lifetime_trials"):
        if through_json:
            type(good).model_validate_json(json.dumps(payload))
        else:
            type(good).model_validate(payload)


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
def test_experiment_normalizes_integral_counts_before_large_sum_and_keeps_legacy_default(
    kind: str,
) -> None:
    maximum = np.uint64(np.iinfo(np.uint64).max)
    result = experiment(kind, 2 * int(maximum) + 10, (maximum, maximum))
    assert type(result.lifetime_trials) is int
    assert all(type(t.n_evaluated_configs) is int for t in result.trials)
    assert sum(t.n_evaluated_configs for t in result.trials) == 2 * int(maximum)
    small = experiment(kind, np.int64(4), (np.int64(4),))
    assert type(small.lifetime_trials) is int
    assert experiment(kind, 1, (None,)).trials[0].n_evaluated_configs == 1
    assert experiment(kind, 0, ()).lifetime_trials == 0
    assert experiment(kind, 100, ()).lifetime_trials == 100
    assert type(result).model_validate_json(result.model_dump_json()) == result


def memory_store(kind: str) -> Any:
    return InMemoryExperimentStore() if kind == "longitudinal" else InMemoryCrossSectionalStore()


def prior(store: Any, kind: str) -> int:
    return store.trials_for_symbol("MANUAL") if kind == "longitudinal" else store.prior_trials()


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
@pytest.mark.parametrize("invalid_leaf", [False, True])
def test_memory_store_rejects_unchecked_counter_copy_before_append(
    kind: str, invalid_leaf: bool
) -> None:
    good = experiment(kind)
    store = memory_store(kind)
    store.add(good)
    before = [row.model_dump(round_trip=True) for row in store.all()]
    if invalid_leaf:
        bad_trial = good.trials[0].model_copy(update={"n_evaluated_configs": True})
        bad = good.model_copy(update={"trials": [bad_trial]})
        message = "n_evaluated_configs"
    else:
        bad = good.model_copy(update={"lifetime_trials": 1})
        message = "lifetime_trials"
    with pytest.raises(ValueError, match=message):
        store.add(bad)
    assert [row.model_dump(round_trip=True) for row in store.all()] == before
    assert prior(store, kind) == 4


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
def test_memory_store_owns_equal_canonical_snapshot_without_replacing_identity_fields(
    kind: str,
) -> None:
    good = experiment(kind)
    store = memory_store(kind)
    store.add(good)
    stored = store.all()[0]
    assert stored is not good
    assert stored.model_dump(round_trip=True) == good.model_dump(round_trip=True)
    assert stored.experiment_id == good.experiment_id
    assert stored.created_at == good.created_at


@pytest.mark.parametrize("kind", ["monolithic", "partitioned", "panel"])
def test_json_store_undercounted_copy_cannot_change_files_or_prior(
    tmp_path: Path, kind: str
) -> None:
    model_kind = "panel" if kind == "panel" else "longitudinal"
    good = experiment(model_kind)
    if kind == "partitioned":
        store: Any = PartitionedExperimentStore(tmp_path / "partitions")
    elif kind == "monolithic":
        store = JsonFileExperimentStore(tmp_path / "pool.json")
    else:
        store = JsonFileCrossSectionalStore(tmp_path / "pool.json")
    store.add(good)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*.json")}
    bad = good.model_copy(update={"lifetime_trials": 1})
    with pytest.raises(ValueError, match="lifetime_trials"):
        store.add(bad)
    assert {
        str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*.json")
    } == before
    assert prior(store, model_kind) == 4


@given(
    kind=st.sampled_from(["longitudinal", "panel"]),
    counts=st.lists(st.integers(min_value=1, max_value=10**6), min_size=1, max_size=10),
    carried_prior=st.integers(min_value=0, max_value=10**12),
)
def test_persisted_accounting_accepts_carried_priors_and_refuses_local_deficits(
    kind: str, counts: list[int], carried_prior: int
) -> None:
    total = sum(counts)
    valid = experiment(kind, total + carried_prior, tuple(counts))
    assert valid.lifetime_trials >= sum(t.n_evaluated_configs for t in valid.trials)
    with pytest.raises(ValueError, match="lifetime_trials"):
        experiment(kind, total - 1, tuple(counts))
