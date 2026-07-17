"""Deterministic universe sharding (ADR-026). `shard_universe` splits a symbol list into N
round-robin slices so each parallel Actions job hunts a representative cross-section of the
universe (not a contiguous alphabetical block). Pure + deterministic → trivially unit-tested."""

import pytest

from app.research.lab.sharding import shard_universe

_SYMBOLS = ["A", "B", "C", "D", "E", "F", "G"]


def test_shard_universe_round_robin_slices_are_strided() -> None:
    assert shard_universe(_SYMBOLS, 3, 0) == ["A", "D", "G"]
    assert shard_universe(_SYMBOLS, 3, 1) == ["B", "E"]
    assert shard_universe(_SYMBOLS, 3, 2) == ["C", "F"]


def test_shard_universe_shards_partition_the_universe_without_overlap() -> None:
    n = 4
    shards = [shard_universe(_SYMBOLS, n, i) for i in range(n)]
    flattened = [s for shard in shards for s in shard]
    assert sorted(flattened) == sorted(_SYMBOLS)  # every symbol exactly once
    assert len(flattened) == len(set(flattened))  # no symbol in two shards


def test_shard_universe_single_shard_returns_everything() -> None:
    assert shard_universe(_SYMBOLS, 1, 0) == _SYMBOLS


def test_shard_universe_more_shards_than_symbols_yields_empty_tail_shards() -> None:
    assert shard_universe(["A", "B"], 5, 0) == ["A"]
    assert shard_universe(["A", "B"], 5, 1) == ["B"]
    assert shard_universe(["A", "B"], 5, 2) == []


def test_shard_universe_is_deterministic() -> None:
    assert shard_universe(_SYMBOLS, 3, 1) == shard_universe(_SYMBOLS, 3, 1)


def test_shard_universe_rejects_non_positive_n_shards() -> None:
    with pytest.raises(ValueError, match="n_shards"):
        shard_universe(_SYMBOLS, 0, 0)


def test_shard_universe_rejects_shard_index_out_of_range() -> None:
    with pytest.raises(ValueError, match="shard_index"):
        shard_universe(_SYMBOLS, 3, 3)


def test_shard_universe_rejects_negative_shard_index() -> None:
    with pytest.raises(ValueError, match="shard_index"):
        shard_universe(_SYMBOLS, 3, -1)
