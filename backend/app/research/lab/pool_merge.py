"""Merge sharded hunt outputs into one research pool (ADR-026).

The daily discovery matrix runs each shard in its own Actions job writing its own experiments; the
consolidation job folds them all back together. Deduping by `experiment_id` keeps the merge
idempotent — re-running a shard (or a retried job) never doubles rows.
"""

from app.research.lab.experiment import Experiment


def merge_experiments(existing: list[Experiment], incoming: list[Experiment]) -> list[Experiment]:
    """Fold `incoming` experiments into `existing`, deduped by `experiment_id`. Existing order is
    preserved; a new id is appended; a colliding id is overwritten by the incoming copy (an
    idempotent re-run replaces, never duplicates)."""
    by_id: dict[object, Experiment] = {e.experiment_id: e for e in existing}
    for experiment in incoming:
        by_id[experiment.experiment_id] = experiment
    return list(by_id.values())
