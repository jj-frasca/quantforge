"""Advance the paper-trading portfolio (ADR-019).

Usage: PYTHONPATH=. uv run python scripts/paper.py [--as-of YYYY-MM-DD]

Freezes every graduate in the research pool as a paper position (default as-of = today), then
fetches fresh daily bars and scores each position ONLY on bars after its freeze date — data the
strategy could not have been fit to. Portfolio + scores persist in-repo. The honest scoreboard is
forward Sharpe vs simply holding the name. Local-only (live network); never in CI.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.paper import JsonFilePaperPortfolio, evaluate_forward, freeze_graduate

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool.json"
PORTFOLIO = DATA / "paper_portfolio.json"
START = datetime(2005, 1, 1, tzinfo=UTC)


def _as_of(args: list[str]) -> datetime:
    if "--as-of" in args:
        raw = args[args.index("--as-of") + 1]
        return datetime.fromisoformat(raw).replace(tzinfo=UTC)
    return datetime.now(UTC)


def main() -> None:
    as_of = _as_of(sys.argv[1:])
    pool = JsonFileExperimentStore(POOL)
    portfolio = JsonFilePaperPortfolio(PORTFOLIO)

    for exp in pool.all():
        if exp.graduate is not None:
            position = freeze_graduate(exp, frozen_at=as_of)
            if portfolio.add(position):
                print(f"froze {position.symbol} / {position.strategy_name} as of {as_of.date()}")

    adapter = YFinanceAdapter()
    now = datetime.now(UTC)
    updated = []
    for position in portfolio.positions():
        frame = bars_to_frame(adapter.fetch_price_bars(position.symbol, START, now))
        score = evaluate_forward(position, frame)
        updated.append(position.model_copy(update={"score": score}))
    portfolio.save(updated)

    print(
        f"\n{'=' * 78}\nPAPER PORTFOLIO — forward performance since freeze (out-of-sample)\n{'=' * 78}"
    )
    print(
        f"{'symbol':<7}{'strategy':<32}{'frozen':>12}{'fwd bars':>9}"
        f"{'fwd ret':>9}{'fwd SR':>8}{'B&H SR':>8}  beats B&H"
    )
    for position in updated:
        s = position.score
        if s is None:
            continue
        beats = "—" if s.forward_bars == 0 else ("YES" if s.beats_buy_and_hold else "no")
        print(
            f"{position.symbol:<7}{position.strategy_name:<32}"
            f"{position.frozen_at.date()!s:>12}{s.forward_bars:>9}"
            f"{s.forward_return * 100:>8.1f}%{s.forward_sharpe:>8.2f}"
            f"{s.buy_and_hold_sharpe:>8.2f}  {beats}"
        )
    pending = sum(1 for p in updated if p.score and p.score.forward_bars == 0)
    if pending:
        print(f"\n{pending} position(s) awaiting forward data (frozen at/after the latest bar).")


if __name__ == "__main__":
    main()
