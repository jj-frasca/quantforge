"""Run one immutable ADR-081 complete-panel batch into a scratch shard.

Usage:
    PYTHONPATH=. uv run python scripts/run_panel_null_batch.py \
        COHORT_JSON SOURCE_NPZ OUT_JSON --code-revision SHA --indices INDEX [INDEX ...]
    PYTHONPATH=. uv run python scripts/run_panel_null_batch.py \
        COHORT_JSON SOURCE_NPZ OUT_JSON --code-revision SHA --range START STOP

Exactly one panel selection is required. ``--range START STOP`` is half-open, so STOP is not
executed. The frozen manifest and prepared-source archive determine the job identity; this command
uses the current production strategy catalog, gate, refinement, and selection policy. It writes
only one exclusive-create scratch shard and refuses the repository's generated ``data/`` tree.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from app.research.lab.gate import GateConfig
from app.research.lab.panel_null import run_production_panel_null_batch
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


def resolve_panel_indices(
    *,
    indices: Sequence[int] | None,
    panel_range: Sequence[int] | None,
) -> tuple[int, ...]:
    """Resolve exactly one explicit unique set or half-open range of global panel indices."""
    if (indices is None) == (panel_range is None):
        raise ValueError("exactly one of indices or panel_range is required")
    if indices is not None:
        resolved = tuple(indices)
        if not resolved:
            raise ValueError("panel selection requires at least one index")
        if any(index < 0 for index in resolved):
            raise ValueError("panel indices must be non-negative")
        if len(set(resolved)) != len(resolved):
            raise ValueError("panel selection contains a duplicate index")
        return resolved

    assert panel_range is not None
    if len(panel_range) != 2:
        raise ValueError("panel_range requires exactly START STOP")
    start, stop = panel_range
    if start < 0:
        raise ValueError("panel range START must be non-negative")
    if stop <= start:
        raise ValueError("panel range STOP must be greater than START")
    return tuple(range(start, stop))


def _require_scratch_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == DATA_ROOT or DATA_ROOT in resolved.parents:
        raise ValueError(f"panel-null batch output must be scratch-only, not under {DATA_ROOT}")
    if path.exists():
        raise FileExistsError(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort_json", type=Path)
    parser.add_argument("source_npz", type=Path)
    parser.add_argument("out_json", type=Path)
    parser.add_argument("--code-revision", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--indices", type=int, nargs="+")
    selection.add_argument("--range", dest="panel_range", type=int, nargs=2)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    panel_indices = resolve_panel_indices(
        indices=args.indices,
        panel_range=args.panel_range,
    )
    _require_scratch_output(args.out_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    run_production_panel_null_batch(
        args.cohort_json,
        args.source_npz,
        code_revision=args.code_revision,
        strategy_names=[entry.name for entry in STRATEGY_CATALOG],
        config=GateConfig(),
        panel_indices=panel_indices,
        output_path=args.out_json,
    )
    print(f"completed panel indices: {len(panel_indices)}")
    print(f"wrote scratch shard    : {args.out_json}")


if __name__ == "__main__":
    main()
