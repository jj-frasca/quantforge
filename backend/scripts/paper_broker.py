"""Place real Alpaca paper orders from the OPEN managed book (ADR-021).

Usage: PYTHONPATH=. uv run python scripts/paper_broker.py

The "prove it with real fills" step: mirror each OPEN `PaperPosition` into a real order on the free
Alpaca **paper** account so P&L shows in the dashboard. For each open name we fetch fresh daily bars,
resolve its frozen strategy's latest signal + last close, equal-weight the book by current account
equity, then `reconcile` the diff against what Alpaca already holds. Idempotent (safe to re-run) and
paper only — the broker constructor refuses any non-paper host (rule 7). Market-closed simply queues
the orders. Local/cloud with keys only (live network); never in CI.

The pure orchestration (`compute_targets`) is network-free and unit-tested; `main` is the thin live
wiring (broker + adapter), smoke-covered by the `@pytest.mark.live` test.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.dependencies import build_data_adapter
from app.execution.alpaca_broker import AlpacaBroker, AlpacaOrder, reconcile
from app.execution.sizing import TargetPosition, equal_weight_targets, quote_position
from app.research.frames import bars_to_frame
from app.research.lab.paper import JsonFilePaperPortfolio, PaperPosition

DATA = Path(__file__).resolve().parents[2] / "data"
PORTFOLIO = DATA / "paper_portfolio.json"
PAPER_URL = "https://paper-api.alpaca.markets"
START = datetime(2005, 1, 1, tzinfo=UTC)


def compute_targets(
    open_positions: list[PaperPosition],
    frame_provider: Callable[[str], pd.DataFrame],
    equity: float,
) -> list[TargetPosition]:
    """Pure orchestration: resolve each OPEN position over its fresh frame into a signed,
    equal-weight whole-share target. A name with no fresh bars is skipped (no quote — its slice
    frees for the active names). Deterministic given `frame_provider`; this is the unit-tested core.
    """
    quotes = []
    for position in open_positions:
        frame = frame_provider(position.symbol)
        if frame.empty:
            continue
        quotes.append(quote_position(position, frame))
    return equal_weight_targets(quotes, equity)


def main() -> None:  # pragma: no cover - live wiring, exercised by the @live smoke
    settings = get_settings()
    portfolio = JsonFilePaperPortfolio(PORTFOLIO)
    open_positions = [p for p in portfolio.positions() if p.status == "open"]
    adapter = build_data_adapter(settings)
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    broker = AlpacaBroker(PAPER_URL, settings.alpaca_api_key, settings.alpaca_secret_key)
    equity = float(broker.account().equity)
    targets = compute_targets(open_positions, frame_provider, equity)
    orders = reconcile(broker, targets)
    _print_summary(open_positions, targets, orders, equity)


def _print_summary(
    open_positions: list[PaperPosition],
    targets: list[TargetPosition],
    orders: list[AlpacaOrder],
    equity: float,
) -> None:  # pragma: no cover - console output for the live run
    print(f"{'=' * 66}\nPAPER BROKER — mirror OPEN book to Alpaca paper (equity ${equity:,.2f})")
    print(f"{'=' * 66}\n{len(open_positions)} open positions → {len(targets)} targets")
    for target in targets:
        print(f"  target {target.symbol:<7}{target.target_qty:>10} sh")
    if not orders:
        print("\nalready at target — no orders placed (idempotent).")
        return
    print(f"\n{len(orders)} order(s) placed:")
    for order in orders:
        print(f"  {order.side:<4} {order.qty:>8} {order.symbol:<7} [{order.status}] {order.id}")


if __name__ == "__main__":
    main()
