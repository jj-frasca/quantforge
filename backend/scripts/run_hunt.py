"""Drive a StrategyLab universe hunt on real max-history daily data (ADR-014/015/016/017).

Usage: PYTHONPATH=. uv run python scripts/run_hunt.py [--value-screen [MIN_SCORE]] [SYMBOL ...]
       (default universe: a large-cap set)

For each symbol: fetch the longest daily history, pull cited SEC-EDGAR fundamentals (best effort),
search every catalog strategy on the in-sample split, score the best on the SEALED holdout, and
apply the deterministic gate + fundamentals veto. Findings accumulate in a JSON research pool
(the per-symbol trial count compounds → the DSR/MinTRL honesty flywheel). Prints a per-symbol
summary and a cross-symbol leaderboard. Local-only (live network); never in CI.

Value (ADR-023, WP-J): a cited `UndervaluationScore` is RECORDED on every hunted name (EDGAR
fundamentals-history + the hunt's own price frame, so no extra price fetch). `--value-screen`
turns on the hard value gate (optional following float = min_score; default 0.5, needs calibration)
so only names that look undervalued are hunted; names below the bar are reported as filtered.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.dependencies import build_data_adapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.universe import rank_experiments, run_universe_hunt
from app.research.lab.value_wiring import (
    cached_frame_provider,
    make_hunt_value_provider,
    parse_value_screen,
)
from app.research.strategies.catalog import STRATEGY_CATALOG

# In-repo research pool so findings survive and are reviewable in git.
POOL = Path(__file__).resolve().parents[2] / "data" / "research_pool.json"
START = datetime(2005, 1, 1, tzinfo=UTC)
USER_AGENT = "QuantForge research jjfrasca10@gmail.com"

# A liquid large-cap universe across sectors — more independent shots on goal.
DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "CRM",
    "ORCL",
    "JPM",
    "V",
    "MA",
    "UNH",
    "JNJ",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "HD",
    "XOM",
    "CVX",
    "DIS",
    "NFLX",
]


def _resolve_symbols(args: list[str]) -> list[str]:
    """A single .txt path -> one symbol per line; else the args as tickers; else the default."""
    if len(args) == 1 and args[0].endswith(".txt"):
        return [s.strip().upper() for s in Path(args[0]).read_text().splitlines() if s.strip()]
    return args or DEFAULT_UNIVERSE


def main() -> None:
    value_config, arg_rest = parse_value_screen(sys.argv[1:])
    symbols = _resolve_symbols(arg_rest)
    names = [entry.name for entry in STRATEGY_CATALOG]
    adapter = build_data_adapter(get_settings())
    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    store = JsonFileExperimentStore(POOL)
    end = datetime.now(UTC)

    def fetch_frame(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, end))

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
    print(f"Hunting {len(symbols)} symbols x {len(names)} strategies{screen_note}...\n")
    result = run_universe_hunt(
        symbols,
        names,
        frame_provider,
        fundamentals_provider=fundamentals_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        value_provider=value_provider,
        value_config=value_config,
        store=store,
        refine=True,
        rationale="universe hunt (refined)",
    )

    for exp in result.experiments:
        best = max(exp.trials, key=lambda t: t.deflated_sharpe)
        screen = exp.fundamental_screen
        fund = "n/a" if screen is None else ("PASS" if screen.passed else "FAIL")
        verdict = "GRADUATED ✅" if exp.graduate else "—"
        print(
            f"{exp.symbol:<6} best {best.strategy_name:<30} DSR {best.deflated_sharpe:>6.2f}  "
            f"PBO {best.pbo:>4.2f}  fundamentals {fund:<4}  {verdict}"
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

    graduates = [e for e in result.experiments if e.graduate]
    survivors = [r for r in rows if r.survives_universe_deflation]
    print(
        f"\n{len(graduates)} graduate(s) out of {len(result.experiments)} symbols "
        f"({len(result.errors)} errors); {len(survivors)} survive universe-level deflation."
    )
    if result.errors:
        print("errors:", ", ".join(f"{s} ({e})" for s, e in result.errors.items()))
    if result.filtered:
        print(
            f"value-screened out {len(result.filtered)}: "
            + ", ".join(f"{s} ({why})" for s, why in list(result.filtered.items())[:10])
        )


if __name__ == "__main__":
    main()
