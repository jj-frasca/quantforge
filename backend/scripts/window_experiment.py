"""ADR-074 decision 3: the pre-registered re-search that removes the window comparison's confound.

Usage: PYTHONPATH=. uv run python scripts/window_experiment.py N_SYMBOLS [OUT_FILE]

ADR-063 extended the search window to 1990 and pre-stated that the pool's median holdout Sharpe
must not fall. That clause is unreadable — the live search family has produced one graduate — so
ADR-074 restated it on the finalist, paired within symbol. The paired reading in `pool_report.py`
is a SURROGATE: both sides' walk-forward OOS Sharpe is denominated in its own window's drift
(ADR-068), and the pre-ADR-063 pool rows predate the paired benchmark, so the drift cannot be
differenced out of them.

This script supplies the missing side. It re-searches a deterministic sample of symbols whose LONG
window already carries `walk_forward_hold_sharpe` at `SEARCH_HISTORY_START = 2005-01-01`, writes
them to its own file, and prints the paired comparison of the pool plus those rows — at which point
`compare_search_windows` reports the drift-controlled excess delta instead of refusing.

The criterion was stated in ADR-074 BEFORE this ran and is not restated here: revisit ADR-063 only
if the paired median excess delta is negative AND its bootstrap 95% CI excludes zero. At n = 40 the
SE of the delta is ≈0.046 against a surrogate effect of -0.038, so a null result at that size is
INCONCLUSIVE, not a pass.

ADR-030: this script is the sole writer of its output file. It never writes `data/research_pool/`,
which it reads as the ADR-062 trial prior only. Local-only (live network); never in CI.
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
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    PriorAwareExperimentStore,
)
from app.research.lab.gate import GateConfig
from app.research.lab.history import PRE_ADR063_SEARCH_START
from app.research.lab.pool_report import compare_search_windows, window_experiment_symbols
from app.research.lab.universe import run_universe_hunt
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"


def main() -> None:
    n_symbols = int(sys.argv[1])
    out_file = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else DATA / "window_experiment" / "adr074.json"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)

    pool = PartitionedExperimentStore(POOL)
    experiments = pool.all()
    symbols = window_experiment_symbols(experiments, n_symbols)
    if not symbols:
        print("no symbol carries the benchmark at the long window only — nothing to re-search")
        return

    adapter = YFinanceAdapter()
    now = datetime.now(UTC)
    store = PriorAwareExperimentStore(writer=JsonFileExperimentStore(out_file), prior=pool)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, PRE_ADR063_SEARCH_START, now))

    print(
        f"ADR-074: re-searching {len(symbols)} symbols from "
        f"{PRE_ADR063_SEARCH_START.date()} x {len(STRATEGY_CATALOG)} strategies -> {out_file}\n"
    )
    result = run_universe_hunt(
        symbols,
        [entry.name for entry in STRATEGY_CATALOG],
        frame_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        store=store,
        refine=True,
        rationale="ADR-074 window experiment (SEARCH_HISTORY_START=2005-01-01)",
    )
    print(
        f"{len(result.experiments)} experiments, {len(result.errors)} error(s), "
        f"yield {result.yield_rate:.0%}"
    )

    window = compare_search_windows([*experiments, *result.experiments])
    if window is None or window.excess_delta_median is None:
        print("\nstill NOT MEASURED — no symbol ended with the benchmark at both windows")
        return
    # The full store is ~1 MB of trial lists and the repo's large-file hook refuses it, so the
    # committed evidence is this summary: the comparison the ADR quotes, plus the sample it was
    # taken over. The store stays on disk beside it (ADR-030 — nothing is deleted).
    summary = out_file.with_name(f"{out_file.stem}_summary.json")
    summary.write_text(
        json.dumps(
            {"symbols": symbols, "comparison": window.model_dump()}, indent=2, sort_keys=True
        )
        + "\n"
    )
    print(f"summary -> {summary}")
    print(
        f"\nADR-074 criterion, paired within symbol (n={window.excess_n} of "
        f"{window.n_symbols} paired symbols):\n"
        f"  drift-controlled excess delta {window.excess_delta_median:+.3f} "
        f"[{window.excess_delta_ci_low:+.3f}, {window.excess_delta_ci_high:+.3f}]\n"
        f"  surrogate (raw OOS) delta     {window.oos_delta_median:+.3f} "
        f"[{window.oos_delta_ci_low:+.3f}, {window.oos_delta_ci_high:+.3f}]"
    )


if __name__ == "__main__":
    main()
