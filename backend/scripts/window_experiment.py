"""ADR-074 decision 3 / ADR-076: the pre-registered re-search that removes the window comparison's
confound, sized and frozen.

Usage, from `backend/`:
    PYTHONPATH=. uv run python scripts/window_experiment.py freeze N   # once, before any search
    PYTHONPATH=. uv run python scripts/window_experiment.py run I K    # shard I of K, resumable
    PYTHONPATH=. uv run python scripts/window_experiment.py report     # only when the sample is done

ADR-063 extended the search window to 1990 and pre-stated that the pool's median holdout Sharpe must
not fall. ADR-074 restated that unreadable clause on the finalist, paired within symbol, and its
paired reading in `pool_report.py` is a SURROGATE: both sides' walk-forward OOS Sharpe is
denominated in its own window's drift (ADR-068). This script supplies the missing side by
re-searching symbols at `PRE_ADR063_SEARCH_START`, at which point the comparison reports the
drift-controlled excess delta instead of refusing.

ADR-076 governs how the answer is read, and three of its decisions are enforced here:

* **The sample is frozen** to `adr076_sample.json` before anything is searched. `freeze` writes it;
  `run` and `report` refuse to proceed without it. The candidate shuffle is over the CURRENT pool,
  so re-deriving the sample on a pool that has grown would silently roll a different experiment.
* **A partial run is not a look.** `run` prints no comparison at all, and `report` refuses until
  every frozen symbol has been searched. Reading an interim interval and then continuing would be a
  look the two-look boundary does not cover.
* **The second look is read at `POCOCK_TWO_LOOK_ALPHA`**, printed first as THE criterion, with the
  95% interval beside it labelled as the level look 1 was read at.

ADR-030: each shard is the sole writer of its own file. Nothing here writes `data/research_pool/`,
which is read as the ADR-062 trial prior only. Local-only (live network); never in CI.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.fundamentals import FundamentalCriteria
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import (
    Experiment,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    PriorAwareExperimentStore,
)
from app.research.lab.gate import GateConfig
from app.research.lab.history import PRE_ADR063_SEARCH_START
from app.research.lab.pool_report import (
    POCOCK_TWO_LOOK_ALPHA,
    compare_search_windows,
    window_experiment_symbols,
    window_experiment_workload,
)
from app.research.lab.universe import run_universe_hunt
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"
EXPERIMENT_DIR = DATA / "window_experiment"
SAMPLE_FILE = EXPERIMENT_DIR / "adr076_sample.json"
SUMMARY_FILE = EXPERIMENT_DIR / "adr076_summary.json"
# Every store of searched rows lives here; the two DERIVED kinds are excluded by suffix rather
# than by name, because ADR-074's own summary sits in this directory and is not an experiment list.


def _evidence_files() -> list[Path]:
    """Every store holding searched rows for this experiment — ADR-074's original run included, so
    its 45 symbols count as done rather than being searched a second time."""
    return [
        path
        for path in sorted(EXPERIMENT_DIR.glob("*.json"))
        if not path.stem.endswith(("_summary", "_sample"))
    ]


def _searched() -> list[Experiment]:
    return [e for path in _evidence_files() for e in JsonFileExperimentStore(path).all()]


def _frozen_sample() -> list[str]:
    if not SAMPLE_FILE.exists():
        raise SystemExit(
            f"no frozen sample at {SAMPLE_FILE} — run `window_experiment.py freeze N` first "
            "(ADR-076 decision 1: the sample is fixed and committed before anything is searched)"
        )
    sample: list[str] = json.loads(SAMPLE_FILE.read_text())
    return sample


def freeze(n_symbols: int) -> None:
    experiments = PartitionedExperimentStore(POOL).all()
    symbols = window_experiment_symbols(experiments, n_symbols)
    if len(symbols) < n_symbols:
        raise SystemExit(f"only {len(symbols)} candidates exist; refusing to freeze {n_symbols}")
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_FILE.write_text(json.dumps(symbols, indent=2) + "\n")
    print(f"froze {len(symbols)} symbols -> {SAMPLE_FILE}\nCOMMIT THIS FILE BEFORE SEARCHING.")


def run(shard_index: int, n_shards: int) -> None:
    frozen = _frozen_sample()
    done = {e.symbol for e in _searched()}
    todo = window_experiment_workload(frozen, done, n_shards=n_shards, shard_index=shard_index)
    if not todo:
        print(f"shard {shard_index}/{n_shards}: nothing left to search")
        return

    pool = PartitionedExperimentStore(POOL)
    out_file = EXPERIMENT_DIR / f"adr076_shard{shard_index}of{n_shards}.json"
    store = PriorAwareExperimentStore(writer=JsonFileExperimentStore(out_file), prior=pool)
    adapter = YFinanceAdapter()
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, PRE_ADR063_SEARCH_START, now))

    print(
        f"shard {shard_index}/{n_shards}: {len(todo)} of {len(frozen)} frozen symbols from "
        f"{PRE_ADR063_SEARCH_START.date()} x {len(STRATEGY_CATALOG)} strategies -> {out_file}"
    )
    result = run_universe_hunt(
        todo,
        [entry.name for entry in STRATEGY_CATALOG],
        frame_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        store=store,
        refine=True,
        rationale="ADR-076 window experiment (SEARCH_HISTORY_START=2005-01-01)",
    )
    # ADR-076 decision 5: no comparison here. A partial run is not a look.
    print(
        f"shard {shard_index}/{n_shards} done: {len(result.experiments)} experiments, "
        f"{len(result.errors)} error(s), yield {result.yield_rate:.0%}"
    )


def report() -> None:
    frozen = _frozen_sample()
    searched = _searched()
    missing = sorted(set(frozen) - {e.symbol for e in searched})
    if missing:
        raise SystemExit(
            f"{len(frozen) - len(missing)} of {len(frozen)} frozen symbols searched — "
            "ADR-076 decision 5: a partial run is not a look, so no comparison is printed. "
            f"Resume with `run I K`. Missing: {', '.join(missing[:8])}"
            f"{' …' if len(missing) > 8 else ''}"
        )

    experiments = [*PartitionedExperimentStore(POOL).all(), *searched]
    boundary = compare_search_windows(experiments, alpha=POCOCK_TWO_LOOK_ALPHA)
    single = compare_search_windows(experiments)
    if boundary is None or single is None or boundary.excess_delta_median is None:
        raise SystemExit("no symbol ended with the benchmark at both windows — nothing to read")

    SUMMARY_FILE.write_text(
        json.dumps(
            {
                "sample": frozen,
                "criterion_alpha": POCOCK_TWO_LOOK_ALPHA,
                "criterion": boundary.model_dump(),
                "at_look_one_alpha": single.model_dump(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"summary -> {SUMMARY_FILE}\n")
    print(
        f"ADR-076, paired within symbol (n={boundary.excess_n} of {boundary.n_symbols} paired "
        f"symbols; frozen sample {len(frozen)}):\n"
        f"  THE CRITERION — drift-controlled excess delta, two-look Pocock boundary "
        f"(alpha {POCOCK_TWO_LOOK_ALPHA})\n"
        f"    {boundary.excess_delta_median:+.3f} "
        f"[{boundary.excess_delta_ci_low:+.3f}, {boundary.excess_delta_ci_high:+.3f}]\n"
        f"  the same estimator at look 1's alpha (0.05), for continuity only\n"
        f"    {single.excess_delta_median:+.3f} "
        f"[{single.excess_delta_ci_low:+.3f}, {single.excess_delta_ci_high:+.3f}]\n"
        f"  surrogate (raw OOS) delta, confounded by drift\n"
        f"    {boundary.oos_delta_median:+.3f} "
        f"[{boundary.oos_delta_ci_low:+.3f}, {boundary.oos_delta_ci_high:+.3f}]"
    )


def main() -> None:
    match sys.argv[1:]:
        case ["freeze", n]:
            freeze(int(n))
        case ["run", index, count]:
            run(int(index), int(count))
        case ["report"]:
            report()
        case _:
            raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
