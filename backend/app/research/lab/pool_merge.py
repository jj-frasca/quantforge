"""Merge sharded hunt outputs into one research pool (ADR-026).

The daily discovery matrix runs each shard in its own Actions job writing its own experiments; the
consolidation job folds them all back together. Deduping by `experiment_id` keeps the merge
idempotent — re-running a shard (or a retried job) never doubles rows.
"""

from collections import defaultdict

from app.research.lab.experiment import Experiment


def prune_pool(
    experiments: list[Experiment], *, keep_non_graduate_per_symbol: int = 5
) -> list[Experiment]:
    """Bound the research pool so its JSON stays under GitHub's 100MB file limit (ADR-026 pool-size
    fix). Keep ALL graduates (the valuable output, cheap) plus the most-recent
    `keep_non_graduate_per_symbol` NON-graduate experiments per symbol; drop the older non-graduate
    bulk. Honesty is preserved because the MinTRL denominator is the MAX cumulative `lifetime_trials`
    (experiment._trials_for_symbol), and the most-recent experiment per symbol -- always kept --
    carries that max, so pruning never lowers the graduation bar."""
    graduates = [e for e in experiments if e.graduate is not None]
    by_symbol: dict[str, list[Experiment]] = defaultdict(list)
    for e in experiments:
        if e.graduate is None:
            by_symbol[e.symbol].append(e)
    kept_non_graduates: list[Experiment] = []
    for exps in by_symbol.values():
        recent_first = sorted(exps, key=lambda e: e.created_at, reverse=True)
        kept_non_graduates.extend(recent_first[:keep_non_graduate_per_symbol])
    return graduates + kept_non_graduates


def merge_experiments(existing: list[Experiment], incoming: list[Experiment]) -> list[Experiment]:
    """Fold `incoming` experiments into `existing`, deduped by `experiment_id`. Existing order is
    preserved; a new id is appended; a colliding id is overwritten by the incoming copy (an
    idempotent re-run replaces, never duplicates)."""
    by_id: dict[object, Experiment] = {e.experiment_id: e for e in existing}
    for experiment in incoming:
        by_id[experiment.experiment_id] = experiment
    return list(by_id.values())
