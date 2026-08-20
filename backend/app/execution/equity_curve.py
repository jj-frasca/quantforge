"""Persistent equity-curve tracking for the paper-trading account (visibility over the ADR-019/021
paper book). Each broker run snapshots the REAL Alpaca account equity into a committed JSON time
series, so account performance is watchable and the honest "are we making money?" question can be
answered against the $100k paper starting equity as forward time accumulates."""

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.execution.alpaca_broker import AlpacaAccount

_PAPER_STARTING_EQUITY = 100_000.0


class EquityPoint(BaseModel):
    """One dated snapshot of the paper account: absolute equity/cash + the cumulative return since
    the paper starting equity (default $100k). `float` is fine here — this is a derived reporting
    series, not an order quantity (backend rule: Decimal is for exact round-trips, not stats).

    `benchmark_return_since_start` / `alpha_since_start` answer the ONLY honest "are we making
    money?" question — is the book beating the market, not just up in absolute terms? A book up 3%
    while the market is up 5% is LOSING 2 points of alpha. Both are nullable: points snapshotted
    before benchmark tracking existed are honestly "not measured", never backfilled."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    equity: float
    cash: float
    n_positions: int
    return_since_start: float
    # Cumulative return of the market benchmark over the same window, and the book's excess over it
    # (return_since_start - benchmark_return_since_start). None when no benchmark was supplied.
    benchmark_return_since_start: float | None = None
    alpha_since_start: float | None = None


def append_equity_point(
    history: list[EquityPoint],
    account: AlpacaAccount,
    *,
    n_positions: int,
    now: datetime,
    starting_equity: float = _PAPER_STARTING_EQUITY,
    benchmark_return: float | None = None,
) -> list[EquityPoint]:
    """Append a snapshot of `account` to the equity curve, computing the cumulative return vs the
    paper starting equity and — when `benchmark_return` (the market's cumulative return over the
    same window) is supplied — the excess return (alpha) over it. Pure and additive — order
    preserved, existing points untouched."""
    equity = float(account.equity)
    return_since_start = equity / starting_equity - 1.0
    alpha = None if benchmark_return is None else return_since_start - benchmark_return
    point = EquityPoint(
        timestamp=now,
        equity=equity,
        cash=float(account.cash),
        n_positions=n_positions,
        return_since_start=return_since_start,
        benchmark_return_since_start=benchmark_return,
        alpha_since_start=alpha,
    )
    return [*history, point]


class JsonFileEquityCurve:
    """JSON-file-backed equity curve, committed in-repo so the account history is reviewable in git
    and renderable on the dashboard. Mirrors the other JsonFile stores (trailing newline)."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def all(self) -> list[EquityPoint]:
        if not self._path.exists():
            return []
        return [EquityPoint.model_validate(item) for item in json.loads(self._path.read_text())]

    def save(self, points: list[EquityPoint]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump(mode="json") for p in points]
        self._path.write_text(json.dumps(payload, indent=2) + "\n")
