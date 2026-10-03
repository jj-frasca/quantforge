"""Scheduled mass-test driver (WP-F, ADR-014/015/020/152).

Usage: PYTHONPATH=. uv run python scripts/hunt.py [SYMBOLS_OR_UNIVERSE.txt]
       (default universe: data/universes/sp500.txt)

Runs the StrategyLab universe hunt on the longest available daily history and persists findings in
data/research_pool/. The paper-forward workflow is the sole production paper-book writer and
promotes committed graduates on its next run (ADR-152). Local-only / cloud cron (live network);
never in CI.

DATA SOURCE (load-bearing): the HUNT forces YFinanceAdapter — the search window starts 1990-01-01
(ADR-063), MinTRL needs every year of it, and Alpaca's free IEX feed only reaches back a few
years (ADR-015). Alpaca is for the recent-only
forward/paper loop (scripts/paper.py), NOT the hunt. Do not swap this for build_data_adapter.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.data.sources.retry import CLOUD
from app.data.sources.yfinance import YFinanceAdapter
from app.research.dataset import ResearchDataset, current_git_revision, fetch_research_dataset
from app.research.fundamentals.distress import make_distress_provider
from app.research.fundamentals.record import load_fundamentals_pool
from app.research.lab.experiment import PartitionedExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.history import SEARCH_HISTORY_START
from app.research.lab.quality_filter import make_quality_provider, parse_quality_screen
from app.research.lab.universe import rank_experiments, run_universe_hunt
from app.research.lab.value_wiring import (
    cached_frame_provider,
    make_hunt_value_provider,
    parse_value_screen,
)
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"  # per-symbol partitions (ADR-032)
FUNDAMENTALS_POOL = DATA / "fundamentals_pool.json"
DEFAULT_UNIVERSE = DATA / "universes" / "sp500.txt"
USER_AGENT = "QuantForge research jjfrasca10@gmail.com"


def _resolve_symbols(args: list[str]) -> list[str]:
    """A single .txt path -> one symbol per line; else the args as tickers; else the sp500 file."""
    if len(args) == 1 and args[0].endswith(".txt"):
        path = Path(args[0])
    elif args:
        return [s.strip().upper() for s in args if s.strip()]
    else:
        path = DEFAULT_UNIVERSE
    return [s.strip().upper() for s in path.read_text().splitlines() if s.strip()]


def main() -> None:
    value_config, arg_rest = parse_value_screen(sys.argv[1:])
    quality_config, arg_rest = parse_quality_screen(arg_rest)
    symbols = _resolve_symbols(arg_rest)
    names = [entry.name for entry in STRATEGY_CATALOG]
    # forced: the hunt searches from 1990 (ADR-063); Alpaca IEX is too short.
    adapter = YFinanceAdapter(retry=CLOUD)
    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    pool = PartitionedExperimentStore(POOL)
    now = datetime.now(UTC)
    git_commit_hash = current_git_revision()

    def fetch_dataset(symbol: str) -> ResearchDataset:
        return fetch_research_dataset(
            adapter,
            symbol,
            SEARCH_HISTORY_START,
            now,
            git_commit_hash=git_commit_hash,
        )

    # One memoized fetch feeds BOTH the backtest and the value price series (no double price load).
    dataset_provider = cached_frame_provider(fetch_dataset)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return dataset_provider(symbol).frame

    def fundamentals_provider(symbol: str) -> FundamentalSnapshot | None:
        try:
            return edgar.fetch(symbol)
        except (ValueError, OSError):
            return None  # ETFs/indices have no 10-K revenue

    # Record-first value (ADR-023): score every name; only enforce the gate when --value-screen given.
    value_provider = make_hunt_value_provider(edgar.fetch_history, frame_provider)
    # ADR-029 4b: quality scores come from the weekly EDGAR sweep's pool, not a per-symbol fetch.
    # The screen only bites when --quality-screen is given; a missing pool leaves it inert.
    quality_provider = make_quality_provider(load_fundamentals_pool(FUNDAMENTALS_POOL))
    # ADR-029 4c: hard financial-distress veto — always on, no config (an unscorable name never
    # vetoes; only extreme, multi-signal distress blocks graduation). The last unwired safety rail.
    distress_provider = make_distress_provider(edgar.fetch_history)
    notes = []
    if value_config is not None:
        notes.append(f"value gate min_score={value_config.min_score}")
    if quality_config is not None:
        notes.append(f"quality gate min_score={quality_config.min_quality_score}")
    screen_note = f" [{'; '.join(notes)}]" if notes else ""
    print(
        f"Hunting {len(symbols)} symbols x {len(names)} strategies "
        f"(yfinance max history){screen_note}...\n"
    )
    result = run_universe_hunt(
        symbols,
        names,
        dataset_provider,
        store=pool,
        fundamentals_provider=fundamentals_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        distress_provider=distress_provider,
        value_provider=value_provider,
        value_config=value_config,
        quality_provider=quality_provider,
        quality_config=quality_config,
        refine=True,
        rationale="scheduled universe hunt (WP-F)",
    )

    rows = rank_experiments(result.experiments)
    print(f"\n{'=' * 72}\nCROSS-SYMBOL LEADERBOARD (top 15)\n{'=' * 72}")
    print(f"{'symbol':<7}{'strategy':<30}{'DSR':>7}{'holdout':>9}  graduated  univ-survivor")
    for row in rows[:15]:
        hold = f"{row.holdout_sharpe:.2f}" if row.holdout_sharpe is not None else "—"
        univ = {True: "YES", False: "no", None: "—"}[row.survives_universe_deflation]
        print(
            f"{row.symbol:<7}{row.strategy_name:<30}{row.deflated_sharpe:>7.2f}{hold:>9}  "
            f"{'YES' if row.graduated else 'no':<9}  {univ}"
        )

    graduates = [e for e in result.experiments if e.graduate is not None]
    print(
        f"\n{len(graduates)} graduate(s) out of {len(result.experiments)} symbols "
        f"({len(result.errors)} errors); paper-forward will reconcile promotions."
    )
    if result.errors:
        shown = list(result.errors.items())[:10]
        print("errors:", ", ".join(f"{s} ({e})" for s, e in shown))
    if result.filtered:
        shown_f = list(result.filtered.items())[:10]
        print(
            f"value-screened out {len(result.filtered)}: "
            + ", ".join(f"{s} ({why})" for s, why in shown_f)
        )

    # No pool rewrite here: retention is applied per partition by PartitionedExperimentStore on
    # every write (ADR-032). The old whole-file prune+overwrite was what raised IsADirectoryError
    # once the pool became a directory.


if __name__ == "__main__":
    main()
