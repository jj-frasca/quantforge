"""Persistent equity-curve tracking for the paper-trading account (visibility over the ADR-019/021
paper book). Each broker run snapshots the REAL Alpaca account equity into a committed JSON time
series, so account performance is watchable and the honest "are we making money?" question can be
answered against the $100k paper starting equity as forward time accumulates."""

import json
from datetime import UTC, datetime
from itertools import pairwise
from math import isfinite
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.execution.alpaca_broker import AlpacaAccount

_PAPER_STARTING_EQUITY = 100_000.0


def _snapshot_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("equity snapshot timestamp must be timezone-aware")
    return value.astimezone(UTC)


class EquityPoint(BaseModel):
    """One dated snapshot of the paper account: absolute equity/cash + the cumulative return since
    the paper starting equity (default $100k). `float` is fine here — this is a derived reporting
    series, not an order quantity (backend rule: Decimal is for exact round-trips, not stats).

    `benchmark_return_since_start` / `alpha_since_start` answer the ONLY honest "are we making
    money?" question — is the book beating the market, not just up in absolute terms? A book up 3%
    while the market is up 5% is LOSING 2 points of alpha. Both are nullable: points snapshotted
    before benchmark tracking existed are honestly "not measured", never backfilled.

    `return_since_start` and `alpha_since_start` deliberately use DIFFERENT baselines (ADR-141):
    the former is against the nominal paper starting equity (a fixed target), the latter is the
    book's return since the benchmark's own inception point (`history[0]`, whatever it actually
    was) minus the benchmark's return over that same window — so alpha is never distorted by
    however far the book had already drifted from the nominal start before tracking began."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False, revalidate_instances="always")

    timestamp: datetime
    equity: float
    cash: float
    n_positions: int = Field(ge=0, strict=True)
    return_since_start: float
    # Cumulative return of the market benchmark since `history[0]` (see append_equity_point), and
    # the book's excess over it measured across that SAME window (ADR-141) — not
    # return_since_start - benchmark_return_since_start, which would compare two different windows.
    benchmark_return_since_start: float | None = None
    alpha_since_start: float | None = None

    @field_validator("timestamp")
    @classmethod
    def _timestamp_utc(cls, value: datetime) -> datetime:
        return _snapshot_utc(value)

    @model_validator(mode="after")
    def _validate_benchmark_pair(self) -> "EquityPoint":
        if (self.benchmark_return_since_start is None) != (self.alpha_since_start is None):
            raise ValueError("benchmark return and alpha must be jointly present or absent")
        return self


def _validate_points(points: list[EquityPoint]) -> list[EquityPoint]:
    """Reconstruct the complete observed ledger before arithmetic or filesystem changes."""
    validated = [EquityPoint.model_validate(point) for point in points]
    if any(current.timestamp <= previous.timestamp for previous, current in pairwise(validated)):
        raise ValueError("equity snapshot timestamps must be strictly increasing")
    return validated


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
    paper starting equity and — when `benchmark_return` (the market's cumulative return since
    `history[0]`, i.e. the benchmark's own inception point) is supplied — the excess return (alpha)
    over it, measured across that same window (ADR-141). Pure and additive — order preserved,
    existing points untouched."""
    history = _validate_points(history)
    now = _snapshot_utc(now)
    if history and now <= history[-1].timestamp:
        raise ValueError("equity snapshot timestamps must be strictly increasing")
    if not isfinite(starting_equity) or starting_equity <= 0.0:
        raise ValueError("starting_equity must be finite and positive")
    equity = float(account.equity)
    return_since_start = equity / starting_equity - 1.0
    if benchmark_return is None:
        alpha = None
    else:
        inception_equity = history[0].equity if history else equity
        if not isfinite(inception_equity) or inception_equity <= 0.0:
            raise ValueError("measured alpha requires finite positive inception equity")
        book_return_since_inception = equity / inception_equity - 1.0
        alpha = book_return_since_inception - benchmark_return
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
        return _validate_points(json.loads(self._path.read_text()))

    def save(self, points: list[EquityPoint]) -> None:
        validated = _validate_points(points)
        payload = [p.model_dump(mode="json") for p in validated]
        serialized = json.dumps(payload, indent=2) + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(serialized)
