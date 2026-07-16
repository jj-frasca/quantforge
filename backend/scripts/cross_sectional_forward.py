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

import pandas as pd

from app.data.sources.yfinance import YFinanceAdapter
from app.research.cross_sectional.forward import (
    CrossSectionalPosition,
    manage_cross_sectional_book,
)
from app.research.cross_sectional.forward_store import JsonFileCrossSectionalBook
from app.research.cross_sectional.hunt import price_panel_from_frames
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.frames import bars_to_frame

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "cross_sectional_pool.json"
BOOK = DATA / "cross_sectional_book.json"
START = datetime(2005, 1, 1, tzinfo=UTC)


def main() -> None:
    store = JsonFileCrossSectionalStore(POOL)
    book_store = JsonFileCrossSectionalBook(BOOK)
    adapter = YFinanceAdapter()  # forced: cross-sectional momentum needs a long common history.
    now = datetime.now(UTC)
    graduates = [e for e in store.all() if e.graduate is not None]

    def panel_provider(position: CrossSectionalPosition) -> pd.DataFrame:
        frames: dict[str, pd.DataFrame] = {}
        for symbol in position.universe_symbols:
            try:
                frames[symbol] = bars_to_frame(adapter.fetch_price_bars(symbol, START, now))
            except (ValueError, KeyError, OSError):
                continue  # a dropped name just narrows the panel; the factor still ranks the rest.
        return price_panel_from_frames(frames)

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
