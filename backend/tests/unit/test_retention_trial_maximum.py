"""Retention must preserve represented DSR/MinTRL priors (ADR-300)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_experiment_store import _experiment

from app.research.lab.experiment import (
    Experiment,
    InMemoryExperimentStore,
    PartitionedExperimentStore,
    Trial,
    retain_recent,
)
from app.research.lab.gate import GateConfig


def _row(count: int, index: int, symbol: str = "AAPL", graduate: bool = False) -> Experiment:
    if graduate:
        payload = _experiment(symbol, 1, prior=count - 1, graduated=True).model_dump()
    else:
        payload = {
            "symbol": symbol,
            "strategy_names": ["test"] if count else [],
            "trials": [
                Trial(
                    strategy_name="test",
                    parameters={},
                    observed_sharpe=1.2,
                    deflated_sharpe=0.5,
                    pbo=0.2,
                    parameter_stability_score=0.7,
                    n_evaluated_configs=min(4, count),
                )
            ]
            if count
            else [],
            "gate_config": GateConfig(),
            "lifetime_trials": count,
            "rationale": "synthetic retention evidence",
        }
    return Experiment.model_validate(
        {
            **payload,
            "experiment_id": UUID(int=index + 1),
            "created_at": datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=index),
        }
    )


def test_retain_recent_preserves_old_maximum_and_original_objects() -> None:
    rows = [_row(n, i) for i, n in enumerate([100, 4, 4, 4, 4, 4, 4])]
    before = [r.model_dump_json() for r in rows]
    kept = retain_recent(rows, 5)
    expected = [rows[i] for i in [6, 5, 4, 3, 2, 0]]
    assert len(kept) == 6
    assert all(actual is original for actual, original in zip(kept, expected, strict=True))
    store = InMemoryExperimentStore()
    for row in kept:
        store.add(row)
    assert store.trials_for_symbol("AAPL") == 100
    assert [r.model_dump_json() for r in rows] == before


def test_retain_recent_selects_first_original_maximum_tie() -> None:
    rows = [_row(n, i) for i, n in enumerate([100, 100, 4, 4])]
    assert retain_recent(rows, 1) == [rows[3], rows[0]]
    # Original order, rather than chronology, breaks maximum-witness ties.
    assert retain_recent([rows[1], rows[0], rows[2], rows[3]], 1) == [rows[3], rows[1]]


@pytest.mark.parametrize("graduate", [False, True])
def test_retain_recent_avoids_extra_witness_when_maximum_already_kept(graduate: bool) -> None:
    rows = [_row(100, 0), _row(100, 1, graduate=graduate), _row(4, 2)]
    expected = [rows[1], rows[2]] if graduate else [rows[2], rows[1]]
    assert retain_recent(rows, 2 if not graduate else 1) == expected


def test_retain_recent_zero_quota_preserves_positive_but_not_zero_prior() -> None:
    rows = [_row(0, 0), _row(7, 1), _row(0, 2, "MSFT")]
    assert retain_recent(rows, 0) == [rows[1]]
    assert retain_recent([], 0) == []


def test_retain_recent_mixed_symbols_preserves_old_output_and_appends_each_witness() -> None:
    rows = [
        _row(100, 0),
        _row(10, 1, "MSFT"),
        _row(4, 2),
        _row(1, 3, "MSFT"),
        _row(20, 4, "NVDA", graduate=True),
    ]
    assert retain_recent(rows, 1) == [rows[4], rows[2], rows[0], rows[3], rows[1]]


@pytest.mark.parametrize("batch", [False, True])
def test_partitioned_store_retains_maximum_across_reload_and_further_writes(
    tmp_path: Path, batch: bool
) -> None:
    directory = tmp_path / "pool"
    rows = [_row(n, i) for i, n in enumerate([100, 4, 4, 4, 4, 4, 4])]
    store = PartitionedExperimentStore(directory, 2)
    if batch:
        store.extend(rows)
    else:
        for row in rows:
            store.add(row)
    reader = PartitionedExperimentStore(directory, 2)
    assert reader.trials_for_symbol("AAPL") == 100
    assert reader.all() == [rows[6], rows[5], rows[0]]
    reader.add(_row(4, 7))
    assert reader.all() == [_row(4, 7), rows[6], rows[0]]
    reader.add(_row(104, 8))
    assert reader.trials_for_symbol("AAPL") == 104
    assert reader.all() == [_row(104, 8), _row(4, 7)]
    reader.extend([_row(104, 8)])
    assert len(reader.all()) == 2


INVALID_QUOTAS = [
    -1,
    True,
    False,
    None,
    1.0,
    1.5,
    "1",
    Decimal(1),
    Fraction(1),
    np.bool_(True),
    np.float64(1),
    float("nan"),
    float("inf"),
]


@pytest.mark.parametrize("quota", INVALID_QUOTAS)
def test_retain_recent_invalid_quota_refuses_before_iteration(quota: object) -> None:
    class Unreadable(list):
        def __iter__(self):
            pytest.fail("invalid quota reached source iteration")

    with pytest.raises(ValueError, match="keep_non_graduate_per_symbol"):
        retain_recent(Unreadable(), quota)  # type: ignore[arg-type]


@pytest.mark.parametrize("quota", INVALID_QUOTAS)
def test_partitioned_store_invalid_quota_refuses_before_path_access(quota: object) -> None:
    class UnreadablePath:
        def __fspath__(self):
            pytest.fail("invalid quota reached filesystem path conversion")

    with pytest.raises(ValueError, match="keep_non_graduate_per_symbol"):
        PartitionedExperimentStore(UnreadablePath(), quota)  # type: ignore[arg-type]


@pytest.mark.parametrize("quota", [0, np.int64(1), np.uint64(2), 10**100])
def test_retention_valid_integral_quota_normalizes_without_wrap(tmp_path: Path, quota: int) -> None:
    rows = [_row(100, 0), _row(4, 1)]
    kept = retain_recent(rows, quota)
    assert max(r.lifetime_trials for r in kept) == 100
    store = PartitionedExperimentStore(tmp_path / "pool", quota)
    store.extend(rows)
    assert store.all() == kept
    assert type(store._keep) is int


@given(
    st.lists(st.tuples(st.sampled_from(["AAPL", "MSFT"]), st.integers(0, 10000)), max_size=30),
    st.integers(0, 6),
)
def test_retention_arbitrary_nonmonotone_histories_preserve_each_prior(
    history: list[tuple[str, int]], quota: int
) -> None:
    rows = [_row(n, i, symbol) for i, (symbol, n) in enumerate(history)]
    kept = retain_recent(rows, quota)
    for symbol in ["AAPL", "MSFT"]:
        original = [r for r in rows if r.symbol == symbol]
        retained = [r for r in kept if r.symbol == symbol]
        assert max((r.lifetime_trials for r in retained), default=0) == max(
            (r.lifetime_trials for r in original), default=0
        )
        assert len(retained) <= quota + 1
    assert all(any(r is source for source in rows) for r in kept)
    assert len({r.experiment_id for r in kept}) == len(kept)
    assert retain_recent(kept, quota) == kept


@pytest.mark.parametrize("quota", [0, 1, 3])
def test_retain_recent_graduate_maximum_needs_no_witness_even_at_zero(quota: int) -> None:
    rows = [_row(100, 0), _row(100, 1, graduate=True), _row(4, 2)]
    expected = [
        rows[1],
        *sorted([rows[0], rows[2]], key=lambda r: r.created_at, reverse=True)[:quota],
    ]
    assert retain_recent(rows, quota) == expected


def test_retain_recent_equal_dates_keep_stable_input_order() -> None:
    rows = [_row(100, 0), _row(4, 1), _row(4, 2)]
    rows[2] = Experiment.model_validate({**rows[2].model_dump(), "created_at": rows[1].created_at})
    assert retain_recent(rows, 1) == [rows[1], rows[0]]


@given(
    st.lists(
        st.tuples(st.sampled_from(["AAPL", "MSFT"]), st.integers(1, 10000), st.booleans()),
        max_size=25,
    ),
    st.integers(0, 5),
)
def test_retention_graduates_and_old_policy_are_preserved(
    history: list[tuple[str, int, bool]], quota: int
) -> None:
    rows = [_row(n, i, symbol, graduate) for i, (symbol, n, graduate) in enumerate(history)]
    graduates = [r for r in rows if r.graduate is not None]
    old = list(graduates)
    for symbol in dict.fromkeys(r.symbol for r in rows if r.graduate is None):
        old.extend(
            sorted(
                [r for r in rows if r.symbol == symbol and r.graduate is None],
                key=lambda r: r.created_at,
                reverse=True,
            )[:quota]
        )
    kept = retain_recent(rows, quota)
    assert kept[: len(graduates)] == graduates
    for symbol in {r.symbol for r in rows}:
        original_max = max(r.lifetime_trials for r in rows if r.symbol == symbol)
        assert max(r.lifetime_trials for r in kept if r.symbol == symbol) == original_max
        assert sum(r.symbol == symbol and r.graduate is None for r in kept) <= quota + 1
    assert [r for r in kept if any(r is x for x in old)] == old
    if all(
        max((r.lifetime_trials for r in old if r.symbol == symbol), default=0)
        == max(r.lifetime_trials for r in rows if r.symbol == symbol)
        for symbol in {r.symbol for r in rows}
    ):
        assert kept == old
