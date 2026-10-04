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
from datetime import UTC, date, datetime, time, timedelta
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.data.sources.base import DataSourceAdapter
from app.dependencies import build_data_adapter
from app.execution.alpaca_broker import AlpacaBroker, AlpacaOrder, reconcile
from app.execution.equity_curve import JsonFileEquityCurve, append_equity_point
from app.execution.sizing import TargetPosition, equal_weight_targets, quote_position
from app.research.dataset import ResearchDataset, current_git_revision, fetch_research_dataset
from app.research.lab.history import RECENT_HISTORY_START
from app.research.lab.paper import JsonFilePaperPortfolio, PaperPosition

DATA = Path(__file__).resolve().parents[2] / "data"
PORTFOLIO = DATA / "paper_portfolio.json"
EQUITY_CURVE = DATA / "equity_curve.json"
PAPER_URL = "https://paper-api.alpaca.markets"
_NEW_YORK = ZoneInfo("America/New_York")


def _completed_close_date(snapshot: datetime) -> date | None:
    if snapshot.tzinfo is None or snapshot.utcoffset() is None:
        raise ValueError("benchmark snapshots must be timezone-aware")
    local = snapshot.astimezone(_NEW_YORK)
    day = local.date()
    if local.weekday() < 5:
        if time(9, 30) <= local.time() < time(16):
            return None
        if local.time() < time(9, 30):
            day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def fetch_benchmark_return(
    adapter: DataSourceAdapter,
    inception: datetime,
    now: datetime,
    *,
    git_commit_hash: str,
) -> float | None:
    """Best-effort completed regular daily-close proxy, never an intraday valuation claim.

    Missing expected weekday anchors (including holidays) remain unmeasured. Both observations
    must be outside regular hours; an intraday inception cannot establish this proxy's baseline.
    """
    try:
        first_date = _completed_close_date(inception)
        last_date = _completed_close_date(now)
        if first_date is None or last_date is None or inception > now:
            return None
        start = datetime.combine(
            inception.astimezone(_NEW_YORK).date() - timedelta(days=14),
            time(),
            tzinfo=_NEW_YORK,
        )
        dataset = fetch_research_dataset(
            adapter,
            "SPY",
            start,
            now,
            git_commit_hash=git_commit_hash,
        )
        frame = dataset.frame
        labels = frame.index.tz_convert(_NEW_YORK)
        if not labels.equals(labels.normalize()):
            return None
        closes = dict(zip(labels.date, frame["close"], strict=True))
        if first_date not in closes or last_date not in closes:
            return None
        result = float(closes[last_date]) / float(closes[first_date]) - 1.0
        return result if isfinite(result) and result > -1.0 else None
    except (ValueError, OSError, ArithmeticError):
        return None


def compute_targets(
    open_positions: list[PaperPosition],
    frame_provider: Callable[[str], ResearchDataset],
    equity: float,
) -> list[TargetPosition]:
    """Pure orchestration: resolve each OPEN position over its fresh frame into a signed,
    equal-weight whole-share target. A name with no fresh bars is skipped (no quote — its slice
    frees for the active names). Deterministic given `frame_provider`; this is the unit-tested core.
    """
    quotes = []
    for position in open_positions:
        try:
            dataset = frame_provider(position.symbol)
            if not isinstance(dataset, ResearchDataset):
                raise TypeError("paper target provider must return ResearchDataset")
            if dataset.quality_report.symbol != position.symbol.strip().upper():
                raise ValueError("paper target dataset symbol does not match position")
        except (ValueError, KeyError, OSError, ArithmeticError):
            continue
        frame = dataset.frame
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
    git_commit_hash = current_git_revision()

    def frame_provider(symbol: str) -> ResearchDataset:
        return fetch_research_dataset(
            adapter,
            symbol,
            RECENT_HISTORY_START,
            now,
            git_commit_hash=git_commit_hash,
        )

    broker = AlpacaBroker(PAPER_URL, settings.alpaca_api_key, settings.alpaca_secret_key)
    account = broker.account()
    equity = float(account.equity)
    targets = compute_targets(open_positions, frame_provider, equity)
    orders = reconcile(broker, targets)

    # Snapshot the real account onto the committed equity curve so performance is watchable over
    # time. SPY uses completed regular closes associated with the account observations (ADR-170),
    # a daily-close proxy rather than exact intraday/after-hours mark attribution. A missing or
    # ambiguous benchmark leaves alpha unmeasured while preserving the account snapshot.
    curve = JsonFileEquityCurve(EQUITY_CURVE)
    history = curve.all()
    benchmark_return = (
        fetch_benchmark_return(
            adapter,
            history[0].timestamp,
            now,
            git_commit_hash=git_commit_hash,
        )
        if history
        else None
    )
    curve.save(
        append_equity_point(
            history,
            account,
            n_positions=len(open_positions),
            now=now,
            benchmark_return=benchmark_return,
        )
    )
    _print_summary(open_positions, targets, orders, equity)
    latest = curve.all()[-1]
    alpha_str = (
        f", alpha {latest.alpha_since_start:+.2%} vs SPY"
        if latest.alpha_since_start is not None
        else ""
    )
    print(
        f"\nequity curve: ${latest.equity:,.2f} "
        f"({latest.return_since_start:+.2%} since $100k start{alpha_str}) -> {EQUITY_CURVE.name}"
    )


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
