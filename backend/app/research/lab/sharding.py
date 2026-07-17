"""Deterministic universe sharding for the sharded parallel daily hunt (ADR-026).

Splitting the universe into N round-robin slices lets each parallel Actions job hunt a
representative cross-section rather than a contiguous alphabetical block, so any single shard
timing out or failing loses a spread of names, not a whole sector.
"""


def shard_universe(symbols: list[str], n_shards: int, shard_index: int) -> list[str]:
    """Return shard `shard_index` of `symbols` split into `n_shards` round-robin slices.

    Round-robin (stride-N) assignment is deterministic and makes every shard a representative
    cross-section of the universe. The N shards partition the input exactly (each symbol in one
    shard); trailing shards are shorter when the count does not divide evenly.

    Notes:
        Raises ValueError when n_shards < 1 or shard_index is outside [0, n_shards).
    """
    if n_shards < 1:
        raise ValueError(f"n_shards must be >= 1, got {n_shards}")
    if not 0 <= shard_index < n_shards:
        raise ValueError(f"shard_index must be in [0, {n_shards}), got {shard_index}")
    return symbols[shard_index::n_shards]
