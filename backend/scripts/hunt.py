"""Scheduled mass-test → auto-promotion driver (WP-F, ADR-014/015/020).

Usage: PYTHONPATH=. uv run python scripts/hunt.py [SYMBOLS_OR_UNIVERSE.txt]
       (default universe: data/universes/sp500.txt)

Runs the StrategyLab universe hunt on the longest available daily history, then hands every pool
graduate to the managed paper book: new winners are auto-frozen as OPEN positions; open ones are
monitored/exited by the ADR-020 lifecycle. Findings persist in data/research_pool.json and the book
in data/paper_portfolio.json — commit both. Local-only / cloud cron (live network); never in CI.

DATA SOURCE (load-bearing): the HUNT forces YFinanceAdapter — MinTRL needs 15-20yr of history and
Alpaca's free IEX feed only reaches back a few years (ADR-015). Alpaca is for the recent-only
forward/paper loop (scripts/paper.py), NOT the hunt. Do not swap this for build_data_adapter.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.scheduled_hunt import hunt_and_promote
from app.research.lab.universe import rank_experiments
from app.research.lab.value_wiring import (
    cached_frame_provider,
    make_hunt_value_provider,
    parse_value_screen,
)
from app.research.strategies.catalog import STRATEGY_CATALOG

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool.json"
PORTFOLIO = DATA / "paper_portfolio.json"
DEFAULT_UNIVERSE = DATA / "universes" / "sp500.txt"
START = datetime(2005, 1, 1, tzinfo=UTC)
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
    symbols = _resolve_symbols(arg_rest)
    names = [entry.name for entry in STRATEGY_CATALOG]
    adapter = YFinanceAdapter()  # forced: the hunt needs 15-20yr; Alpaca IEX is too short.
    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    pool = JsonFileExperimentStore(POOL)
    portfolio = JsonFilePaperPortfolio(PORTFOLIO)
    now = datetime.now(UTC)

    def fetch_frame(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    # One memoized fetch feeds BOTH the backtest and the value price series (no double price load).
    frame_provider = cached_frame_provider(fetch_frame)

    def fundamentals_provider(symbol: str) -> FundamentalSnapshot | None:
        try:
            return edgar.fetch(symbol)
        except (ValueError, OSError):
            return None  # ETFs/indices have no 10-K revenue

    # Record-first value (ADR-023): score every name; only enforce the gate when --value-screen given.
    value_provider = make_hunt_value_provider(edgar.fetch_history, frame_provider)
    screen_note = (
        "" if value_config is None else f" [value gate min_score={value_config.min_score}]"
    )
    print(
        f"Hunting {len(symbols)} symbols x {len(names)} strategies "
        f"(yfinance max history){screen_note}...\n"
    )
    result = hunt_and_promote(
        symbols,
        names,
        frame_provider,
        pool=pool,
        portfolio=portfolio,
        fundamentals_provider=fundamentals_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        value_provider=value_provider,
        value_config=value_config,
        now=now,
        refine=True,
        rationale="scheduled universe hunt (WP-F)",
    )

    for position in result.promoted:
        print(f"PROMOTED {position.symbol} / {position.strategy_name} (frozen {now.date()})")

    rows = rank_experiments(result.hunt.experiments)
    print(f"\n{'=' * 72}\nCROSS-SYMBOL LEADERBOARD (top 15)\n{'=' * 72}")
    print(f"{'symbol':<7}{'strategy':<30}{'DSR':>7}{'holdout':>9}  graduated  univ-survivor")
    for row in rows[:15]:
        hold = f"{row.holdout_sharpe:.2f}" if row.holdout_sharpe is not None else "—"
        univ = {True: "YES", False: "no", None: "—"}[row.survives_universe_deflation]
        print(
            f"{row.symbol:<7}{row.strategy_name:<30}{row.deflated_sharpe:>7.2f}{hold:>9}  "
            f"{'YES' if row.graduated else 'no':<9}  {univ}"
        )

    graduates = [e for e in result.hunt.experiments if e.graduate is not None]
    n_open = sum(1 for p in result.positions if p.status == "open")
    n_closed = sum(1 for p in result.positions if p.status == "closed")
    print(
        f"\n{len(graduates)} graduate(s) out of {len(result.hunt.experiments)} symbols "
        f"({len(result.hunt.errors)} errors); {len(result.promoted)} promoted this run. "
        f"Managed book: {n_open} open, {n_closed} closed."
    )
    if result.hunt.errors:
        shown = list(result.hunt.errors.items())[:10]
        print("errors:", ", ".join(f"{s} ({e})" for s, e in shown))
    if result.hunt.filtered:
        shown_f = list(result.hunt.filtered.items())[:10]
        print(
            f"value-screened out {len(result.hunt.filtered)}: "
            + ", ".join(f"{s} ({why})" for s, why in shown_f)
        )


if __name__ == "__main__":
    main()
