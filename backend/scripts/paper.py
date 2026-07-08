"""Advance the MANAGED paper portfolio (ADR-019/020).

Usage: PYTHONPATH=. uv run python scripts/paper.py

One managed step: PROMOTE every research-pool graduate we don't already hold, MONITOR each open
position on fresh daily bars (scored ONLY on data after its freeze), and EXIT any that deteriorate
(rolling-Sharpe decay, forward-drawdown breach, or no longer beating buy-and-hold). Winners in,
losers cut — automatically. Portfolio persists in-repo. Local-only (live network); never in CI.
"""

from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.dependencies import build_data_adapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.portfolio_manager import manage_portfolio

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool.json"
PORTFOLIO = DATA / "paper_portfolio.json"
START = datetime(2005, 1, 1, tzinfo=UTC)


def main() -> None:
    pool = JsonFileExperimentStore(POOL)
    portfolio = JsonFilePaperPortfolio(PORTFOLIO)
    adapter = build_data_adapter(get_settings())
    now = datetime.now(UTC)

    def frame_provider(symbol: str):
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    graduates = [e for e in pool.all() if e.graduate is not None]
    before = {p.symbol for p in portfolio.positions()}
    updated = manage_portfolio(portfolio.positions(), graduates, frame_provider, now=now)
    portfolio.save(updated)

    for position in updated:
        if position.symbol not in before:
            print(f"PROMOTED {position.symbol} / {position.strategy_name} (frozen {now.date()})")
        if position.status == "closed" and position.closed_at == now:
            print(
                f"EXITED   {position.symbol} / {position.strategy_name}: "
                f"{'; '.join(position.exit_reasons)}"
            )

    print(f"\n{'=' * 82}\nMANAGED PAPER PORTFOLIO — forward performance since freeze\n{'=' * 82}")
    print(
        f"{'symbol':<7}{'strategy':<30}{'status':>8}{'fwd bars':>9}"
        f"{'fwd ret':>9}{'fwd SR':>8}{'B&H SR':>8}  beats"
    )
    for position in updated:
        s = position.score
        if s is None:
            continue
        beats = "—" if s.forward_bars == 0 else ("YES" if s.beats_buy_and_hold else "no")
        print(
            f"{position.symbol:<7}{position.strategy_name:<30}{position.status:>8}"
            f"{s.forward_bars:>9}{s.forward_return * 100:>8.1f}%{s.forward_sharpe:>8.2f}"
            f"{s.buy_and_hold_sharpe:>8.2f}  {beats}"
        )
    n_open = sum(1 for p in updated if p.status == "open")
    n_closed = sum(1 for p in updated if p.status == "closed")
    print(f"\n{n_open} open, {n_closed} closed.")


if __name__ == "__main__":
    main()
