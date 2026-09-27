"""Cross-sectional forward-testing driver (ADR-025).

Usage: PYTHONPATH=. uv run python scripts/cross_sectional_forward.py

Advances the cross-sectional forward book one step: promotes any pool graduate not yet tracked into
an OPEN forward position, recomputes each open factor's out-of-sample portfolio returns on fresh
bars vs the equal-weight benchmark, and RETIRES the ones that have decayed (rolling-Sharpe floor /
drawdown / stops beating the benchmark). The managed book persists in data/cross_sectional_book.json
so a decaying factor is cut like real money. Local-only / cloud cron (live network); never in CI.

DATA SOURCE: forces YFinanceAdapter (long common history), same rationale as the hunt driver.
"""

from datetime import UTC, datetime
from pathlib import Path

from app.data.sources.retry import CLOUD
from app.data.sources.yfinance import YFinanceAdapter
from app.research.cross_sectional.forward import (
    CrossSectionalPosition,
    manage_cross_sectional_book,
)
from app.research.cross_sectional.forward_store import JsonFileCrossSectionalBook
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.dataset import ResearchDataset, current_git_revision, fetch_research_dataset
from app.research.lab.history import RECENT_HISTORY_START

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "cross_sectional_pool.json"
BOOK = DATA / "cross_sectional_book.json"


def main() -> None:
    store = JsonFileCrossSectionalStore(POOL)
    book_store = JsonFileCrossSectionalBook(BOOK)
    # forced: cross-sectional momentum needs a long common history.
    adapter = YFinanceAdapter(retry=CLOUD)
    now = datetime.now(UTC)
    git_commit_hash = current_git_revision()
    graduates = [e for e in store.all() if e.graduate is not None]

    def panel_provider(position: CrossSectionalPosition) -> dict[str, ResearchDataset]:
        return {
            symbol: fetch_research_dataset(
                adapter,
                symbol,
                RECENT_HISTORY_START,
                now,
                git_commit_hash=git_commit_hash,
            )
            for symbol in position.universe_symbols
        }

    positions = manage_cross_sectional_book(
        book_store.positions(), graduates, panel_provider, now=now
    )
    book_store.save(positions)

    n_open = sum(1 for p in positions if p.status == "open")
    n_retired = sum(1 for p in positions if p.status == "retired")
    print(
        f"cross-sectional forward book: {n_open} open, {n_retired} retired "
        f"({len(graduates)} pool graduates)\n"
    )
    for position in positions:
        score = position.score
        line = f"{position.strategy_name:<14}{position.status:<9}"
        if score is not None:
            line += (
                f"fwd_bars={score.forward_bars:<5} fwd_sharpe={score.forward_sharpe:>6.2f} "
                f"beats_benchmark={score.beats_benchmark}"
            )
        if position.exit_reasons:
            line += " | " + "; ".join(position.exit_reasons)
        print(line)


if __name__ == "__main__":
    main()
