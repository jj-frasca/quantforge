"""Consolidate the daily discovery matrix (ADR-026).

Usage: PYTHONPATH=. uv run python scripts/consolidate_pool.py SHARD_DIR POOL_DIR

Merges every shard pool JSON in SHARD_DIR into the per-symbol pool POOL_DIR (dedup by
experiment_id — idempotent, ADR-032). The paper-forward workflow is the sole production writer of
the managed paper book and promotes committed graduates on its next run (ADR-152). Committed by the
workflow in a single commit, so N parallel shards never race to write the pool. Local-only / cloud;
never in CI.
"""

import sys
from pathlib import Path

from app.research.lab.experiment import (
    Experiment,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
)
from app.research.lab.pool_merge import merge_experiments


def main() -> None:
    shard_dir = Path(sys.argv[1])
    pool_dir = Path(sys.argv[2])

    pool = PartitionedExperimentStore(pool_dir)
    incoming: list[Experiment] = []
    shard_files = sorted(shard_dir.glob("*.json"))
    for shard_file in shard_files:
        incoming = merge_experiments(incoming, JsonFileExperimentStore(shard_file).all())
    # One partition write per touched symbol; retention is applied by the store (ADR-032), so the
    # pool stays bounded no matter which writer got here.
    pool.extend(incoming)
    merged = pool.all()
    graduates = [e for e in merged if e.graduate is not None]
    print(
        f"consolidated {len(shard_files)} shard(s) -> {len(merged)} experiments "
        f"({len(incoming)} incoming), {len(graduates)} graduate(s); "
        "paper-forward will reconcile promotions"
    )


if __name__ == "__main__":
    main()
