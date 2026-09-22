"""ADR-094: the pre-registered truncated re-search that isolates history length from cohort
composition on the 7,400-vs-9,247-bar excess-magnitude question.

Usage, from `backend/`:
    PYTHONPATH=. uv run python scripts/history_length_experiment.py freeze N   # once, before search
    PYTHONPATH=. uv run python scripts/history_length_experiment.py run I K    # shard I of K, resumable
    PYTHONPATH=. uv run python scripts/history_length_experiment.py report     # only when sample is done

Three same-day calibration dispatches found the pool's walk-forward excess non-monotonic across
6,075/7,400/9,247-bar cohorts (`ARCHITECTURE.md` §0.6.1), with the 7,400-bar cohort's excess larger
in magnitude than the 9,247-bar cohort's. This script asks whether that gap is a history-length
effect or a cohort-composition effect (the 9,247-bar cohort is, by ADR-063's construction, exactly
"every symbol listed before 1990") by re-searching symbols from the 9,247-bar cohort using only
their own most recent `CALIBRATION_N_BARS` (7,400) rows and pairing each symbol's truncated excess
against its natural one.

Follows ADR-076's pattern exactly:

* **The sample is frozen** to `adr094_sample.json` before anything is searched. `freeze` writes it;
  `run` and `report` refuse to proceed without it.
* **A partial run is not a look.** `report` refuses until every frozen symbol has been searched.
* **This is a single, unsized first look** (ADR-094 decision 4) — no Pocock boundary, read at the
  nominal 95% interval.

ADR-030: each shard is the sole writer of its own file. Nothing here writes `data/research_pool/`.
Local-only (live network); never in CI.
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
from app.research.lab.history import CALIBRATION_N_BARS, SEARCH_HISTORY_START
from app.research.lab.pool_report import compare_search_windows, history_length_experiment_symbols
from app.research.lab.sharding import shard_universe
from app.research.lab.universe import run_universe_hunt
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"
EXPERIMENT_DIR = DATA / "history_length_experiment"
SAMPLE_FILE = EXPERIMENT_DIR / "adr094_sample.json"
SUMMARY_FILE = EXPERIMENT_DIR / "adr094_summary.json"
# The two sides of ADR-094's pairing both already sit at or above WINDOW_SPLIT_BARS (6000), so the
# default split in `compare_search_windows` would bucket them together. 8000 sits with clear
# headroom between the truncation target (7400) and the candidate floor (8500).
SPLIT_BARS = 8000
MIN_NATURAL_N_BARS = 8500


def _evidence_files() -> list[Path]:
    """Every store holding searched rows for this experiment."""
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
            f"no frozen sample at {SAMPLE_FILE} — run `history_length_experiment.py freeze N` "
            "first (ADR-094 decision 3: the sample is fixed and committed before anything is "
            "searched)"
        )
    sample: list[str] = json.loads(SAMPLE_FILE.read_text())
    return sample


def freeze(n_symbols: int) -> None:
    experiments = PartitionedExperimentStore(POOL).all()
    symbols = history_length_experiment_symbols(experiments, MIN_NATURAL_N_BARS, n_symbols)
    if len(symbols) < n_symbols:
        raise SystemExit(f"only {len(symbols)} candidates exist; refusing to freeze {n_symbols}")
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_FILE.write_text(json.dumps(symbols, indent=2) + "\n")
    print(f"froze {len(symbols)} symbols -> {SAMPLE_FILE}\nCOMMIT THIS FILE BEFORE SEARCHING.")


def run(shard_index: int, n_shards: int) -> None:
    frozen = _frozen_sample()
    done = {e.symbol for e in _searched()}
    todo = [s for s in shard_universe(frozen, n_shards, shard_index) if s not in done]
    if not todo:
        print(f"shard {shard_index}/{n_shards}: nothing left to search")
        return

    pool = PartitionedExperimentStore(POOL)
    out_file = EXPERIMENT_DIR / f"adr094_shard{shard_index}of{n_shards}.json"
    store = PriorAwareExperimentStore(writer=JsonFileExperimentStore(out_file), prior=pool)
    adapter = YFinanceAdapter()
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        full = bars_to_frame(adapter.fetch_price_bars(symbol, SEARCH_HISTORY_START, now))
        return full.tail(CALIBRATION_N_BARS)

    print(
        f"shard {shard_index}/{n_shards}: {len(todo)} of {len(frozen)} frozen symbols, truncated "
        f"to {CALIBRATION_N_BARS} bars x {len(STRATEGY_CATALOG)} strategies -> {out_file}"
    )
    result = run_universe_hunt(
        todo,
        [entry.name for entry in STRATEGY_CATALOG],
        frame_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        store=store,
        refine=True,
        rationale=f"ADR-094 history-length experiment (truncated to {CALIBRATION_N_BARS} bars)",
    )
    # ADR-094 decision 5: no comparison here. A partial run is not a look.
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
            "ADR-094 decision 5: a partial run is not a look, so no comparison is printed. "
            f"Resume with `run I K`. Missing: {', '.join(missing[:8])}"
            f"{' …' if len(missing) > 8 else ''}"
        )

    experiments = [*PartitionedExperimentStore(POOL).all(), *searched]
    comparison = compare_search_windows(experiments, split_bars=SPLIT_BARS)
    if comparison is None or comparison.excess_delta_median is None:
        raise SystemExit("no symbol ended with the benchmark at both sides — nothing to read")

    SUMMARY_FILE.write_text(
        json.dumps(
            {"sample": frozen, "split_bars": SPLIT_BARS, "comparison": comparison.model_dump()},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"summary -> {SUMMARY_FILE}\n")
    print(
        f"ADR-094, paired within symbol (n={comparison.excess_n} of {comparison.n_symbols} paired "
        f"symbols; frozen sample {len(frozen)}; truncated {comparison.short_n_bars} vs natural "
        f"{comparison.long_n_bars} bars):\n"
        f"  drift-controlled excess delta (natural minus truncated), single look at 95%\n"
        f"    {comparison.excess_delta_median:+.3f} "
        f"[{comparison.excess_delta_ci_low:+.3f}, {comparison.excess_delta_ci_high:+.3f}]\n"
        f"  surrogate (raw OOS) delta, confounded by drift\n"
        f"    {comparison.oos_delta_median:+.3f} "
        f"[{comparison.oos_delta_ci_low:+.3f}, {comparison.oos_delta_ci_high:+.3f}]\n"
        f"  finalist strategy changed on {comparison.n_finalist_changed} of {comparison.n_symbols}"
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
