"""Prepare immutable scratch inputs for ADR-081's replicated panel-null measurement.

Usage:
    PYTHONPATH=. uv run python scripts/prepare_panel_null.py ASOF_UTC SOURCE_NPZ COHORT_JSON \
        --base-seed SEED --code-revision SHA [--pool-dir PATH] [--target-n-bars N]

``ASOF_UTC`` is required and must carry a zero UTC offset. The exact same instant bounds every
yfinance request and removes its still-forming UTC-date bar. This command reads the committed
research pool, uses ADR-031's shared cloud retry policy, and writes only the two exclusive-create
scratch artifacts. It refuses paths under the repository's generated ``data/`` tree; only the
separate consolidator may write the eventual final artifact there (ADR-030/081).
"""

import argparse
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd

from app.data.models import PriceBar
from app.data.sources.retry import CLOUD, RetryPolicy
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.calibration import calibration_search_version, drop_incomplete_bars
from app.research.lab.experiment import Experiment, PartitionedExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.history import CALIBRATION_N_BARS, SEARCH_HISTORY_START
from app.research.lab.panel_null import (
    PANEL_NULL_DIAGNOSTIC_VERSION,
    PANEL_NULL_GENERATOR_VERSION,
    PanelNullCohort,
    SelectedPanelNullCohort,
    bind_panel_null_cohort,
    fetch_panel_null_source,
    make_production_panel_null_search,
    measure_observed_panel_excesses,
    save_panel_null_cohort,
    save_prepared_panel_null_source,
    select_panel_null_cohort,
)
from app.research.lab.pool_report import HISTORY_TOLERANCE, MIN_MATCHED
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
DEFAULT_POOL = DATA_ROOT / "research_pool"


class _PriceAdapter(Protocol):
    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]: ...


class _AdapterFactory(Protocol):
    def __call__(self, *, retry: RetryPolicy) -> _PriceAdapter: ...


def parse_utc_instant(value: str) -> datetime:
    """Parse one explicit zero-offset instant without silently assuming a timezone."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"ASOF_UTC must be an ISO-8601 timezone-aware UTC instant: {value!r}"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"ASOF_UTC must be an ISO-8601 timezone-aware UTC instant: {value!r}")
    return parsed.astimezone(UTC)


def _require_scratch_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == DATA_ROOT or DATA_ROOT in resolved.parents:
        raise ValueError(
            f"panel-null preparation output must be scratch-only, not under {DATA_ROOT}"
        )
    if path.exists():
        raise FileExistsError(path)


def prepare_panel_null_source_files(
    selected: SelectedPanelNullCohort,
    *,
    asof: datetime,
    source_path: Path,
    manifest_path: Path,
    base_seed: int,
    code_revision: str,
    adapter_factory: _AdapterFactory = YFinanceAdapter,
    search: Callable[[pd.DataFrame, str], Experiment] | None = None,
) -> PanelNullCohort:
    """Fetch one source panel, remeasure its observed statistic, and freeze both inputs."""
    asof = parse_utc_instant(asof.isoformat())
    source_path = Path(source_path)
    manifest_path = Path(manifest_path)
    if source_path.resolve() == manifest_path.resolve():
        raise ValueError("source archive and cohort manifest paths must be different")
    _require_scratch_output(source_path)
    _require_scratch_output(manifest_path)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    adapter = adapter_factory(retry=CLOUD)

    def fetch_frame(symbol: str) -> pd.DataFrame:
        bars = adapter.fetch_price_bars(symbol, SEARCH_HISTORY_START, asof)
        return drop_incomplete_bars(bars_to_frame(bars), asof=asof)

    prepared = fetch_panel_null_source(selected, fetch_frame)
    if search is None:
        search = make_production_panel_null_search(
            selected,
            [entry.name for entry in STRATEGY_CATALOG],
            config=GateConfig(),
            n_per_param=3,
            refine=True,
            refine_span=0.25,
            select_by="observed",
        )
    observed = measure_observed_panel_excesses(selected, prepared, search=search)
    selected = selected.model_copy(update={"symbol_excesses": observed})
    cohort = bind_panel_null_cohort(
        selected,
        prepared,
        generator_version=PANEL_NULL_GENERATOR_VERSION,
        diagnostic_version=PANEL_NULL_DIAGNOSTIC_VERSION,
        base_seed=base_seed,
        code_revision=code_revision,
    )
    save_prepared_panel_null_source(prepared, source_path)
    save_panel_null_cohort(cohort, manifest_path)
    return cohort


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asof_utc", type=parse_utc_instant)
    parser.add_argument("source_npz", type=Path)
    parser.add_argument("cohort_json", type=Path)
    parser.add_argument("--base-seed", type=int, required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--pool-dir", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--target-n-bars", type=int, default=CALIBRATION_N_BARS)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    config = GateConfig()
    strategy_names = [entry.name for entry in STRATEGY_CATALOG]
    search_version = calibration_search_version(
        strategy_names,
        n_per_param=3,
        config=config,
        refine=True,
        refine_span=0.25,
        select_by="observed",
    )
    experiments = PartitionedExperimentStore(args.pool_dir).all()
    selected = select_panel_null_cohort(
        experiments,
        target_n_bars=args.target_n_bars,
        history_tolerance=HISTORY_TOLERANCE,
        search_config_version=search_version,
        gate_config_version=config.version_hash,
        min_symbols=MIN_MATCHED,
    )
    cohort = prepare_panel_null_source_files(
        selected,
        asof=args.asof_utc,
        source_path=args.source_npz,
        manifest_path=args.cohort_json,
        base_seed=args.base_seed,
        code_revision=args.code_revision,
    )
    print(f"frozen symbols        : {len(cohort.symbols)}")
    print(f"completed source range: {cohort.source_start} -> {cohort.source_end}")
    print(f"source digest         : {cohort.source_sha256}")
    print(f"search config version : {cohort.search_config_version}")
    print(f"gate config version   : {cohort.gate_config_version}")
    print(f"executed code revision: {cohort.code_revision}")
    print(f"wrote source archive  : {args.source_npz}")
    print(f"wrote cohort manifest : {args.cohort_json}")


if __name__ == "__main__":
    main()
