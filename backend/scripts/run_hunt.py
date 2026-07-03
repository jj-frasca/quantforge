"""Drive a StrategyLab universe hunt on real max-history daily data (ADR-014/015/016/017).

Usage: PYTHONPATH=. uv run python scripts/run_hunt.py [SYMBOL ...]   (default: a large-cap universe)

For each symbol: fetch the longest daily history, pull cited SEC-EDGAR fundamentals (best effort),
search every catalog strategy on the in-sample split, score the best on the SEALED holdout, and
apply the deterministic gate + fundamentals veto. Findings accumulate in a JSON research pool
(the per-symbol trial count compounds → the DSR/MinTRL honesty flywheel). Prints a per-symbol
summary and a cross-symbol leaderboard. Local-only (live network); never in CI.
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
from app.research.lab.universe import rank_experiments, run_universe_hunt
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
    symbols = _resolve_symbols(sys.argv[1:])
    names = [entry.name for entry in STRATEGY_CATALOG]
    adapter = YFinanceAdapter()
    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    store = JsonFileExperimentStore(POOL)
    end = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, end))

    def fundamentals_provider(symbol: str) -> FundamentalSnapshot | None:
        try:
            return edgar.fetch(symbol)
        except (ValueError, OSError):
            return None  # ETFs/indices have no 10-K revenue

    print(f"Hunting {len(symbols)} symbols x {len(names)} strategies...\n")
    result = run_universe_hunt(
        symbols,
        names,
        frame_provider,
        fundamentals_provider=fundamentals_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
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

    print(f"\n{'=' * 66}\nCROSS-SYMBOL LEADERBOARD (top 15 by graduated, then DSR)\n{'=' * 66}")
    print(f"{'symbol':<7}{'strategy':<30}{'DSR':>7}{'holdout':>9}  graduated")
    for row in rank_experiments(result.experiments)[:15]:
        hold = f"{row.holdout_sharpe:.2f}" if row.holdout_sharpe is not None else "—"
        print(
            f"{row.symbol:<7}{row.strategy_name:<30}{row.deflated_sharpe:>7.2f}{hold:>9}  "
            f"{'YES' if row.graduated else 'no'}"
        )

    graduates = [e for e in result.experiments if e.graduate]
    print(
        f"\n{len(graduates)} graduate(s) out of {len(result.experiments)} symbols "
        f"({len(result.errors)} errors)."
    )
    if result.errors:
        print("errors:", ", ".join(f"{s} ({e})" for s, e in result.errors.items()))


if __name__ == "__main__":
    main()
