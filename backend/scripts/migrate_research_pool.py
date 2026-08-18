"""One-shot ADR-032 migration: split data/research_pool.json into per-symbol partitions.

Usage: PYTHONPATH=. uv run python scripts/migrate_research_pool.py [SOURCE] [POOL_DIR]

The single-file pool passed GitHub's 100MB push limit, so the scientific record became unwritable.
This splits it into data/research_pool/<SYMBOL>.json. Lossless: the source is removed only after the
partitions are verified to hold exactly the same experiment ids, and a non-empty destination is
refused so a re-run cannot duplicate the record. Idempotent — a second run is a no-op.
"""

import sys
from pathlib import Path

from app.research.lab.experiment import PartitionedExperimentStore, migrate_pool_to_partitions

DATA = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "research_pool.json"
    pool_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DATA / "research_pool"

    migrated = migrate_pool_to_partitions(source, pool_dir)
    if migrated == 0:
        print(f"nothing to migrate ({source} absent or empty) — already partitioned?")
    store = PartitionedExperimentStore(pool_dir)
    partitions = sorted(pool_dir.glob("*.json")) if pool_dir.exists() else []
    largest = max((p.stat().st_size for p in partitions), default=0)
    print(
        f"migrated {migrated} experiment(s) -> {len(partitions)} partition(s) in {pool_dir}; "
        f"{len(store.all())} readable; largest partition {largest / 1e6:.2f} MB"
    )


if __name__ == "__main__":
    main()
