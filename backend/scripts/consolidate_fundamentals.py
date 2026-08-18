"""Consolidate the fundamental discovery sweep (ADR-029 Layer 3).

Usage: PYTHONPATH=. uv run python scripts/consolidate_fundamentals.py SHARD_DIR MAIN_POOL

Merges every shard's fundamentals JSON in SHARD_DIR into MAIN_POOL (data/fundamentals_pool.json),
deduping by CIK and keeping the newest filing — so re-running a shard is idempotent and the pool
stays bounded at one row per company. Then prints the leaderboard: the genuinely good, reasonably
priced companies (ranked by combined quality*value, with a quality-only fallback). Committed by the
workflow in a single commit so N parallel shards never race to write the pool. Live/cloud, not CI.
"""

import json
import sys
from pathlib import Path

from app.research.fundamentals.record import (
    FundamentalRecord,
    merge_fundamental_records,
    rank_fundamentals,
)


def _load(path: Path) -> list[FundamentalRecord]:
    if not path.exists():
        return []
    return [FundamentalRecord.model_validate(row) for row in json.loads(path.read_text())]


def main() -> None:
    shard_dir = Path(sys.argv[1])
    main_pool = Path(sys.argv[2])

    merged = _load(main_pool)
    shard_files = sorted(shard_dir.glob("fundamentals_shard_*.json"))
    for shard_file in shard_files:
        merged = merge_fundamental_records(merged, _load(shard_file))

    main_pool.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.model_dump(mode="json") for r in merged]
    main_pool.write_text(json.dumps(payload, indent=2) + "\n")

    combined = rank_fundamentals(merged, by="combined", top=20)
    board = combined if combined else rank_fundamentals(merged, by="quality", top=20)
    basis = "combined quality*value" if combined else "quality (no priced names yet)"
    print(
        f"consolidated {len(shard_files)} shard(s) -> {len(merged)} companies in the pool.\n"
        f"Top {len(board)} by {basis}:"
    )
    for r in board:
        score = r.combined_score if combined else r.quality_score
        val = f"{r.value_score:.2f}" if r.value_score is not None else "  — "
        print(f"  {r.symbol:<7} score={score:.3f}  F={r.f_score}  value={val}  (FY{r.fiscal_year})")


if __name__ == "__main__":
    main()
