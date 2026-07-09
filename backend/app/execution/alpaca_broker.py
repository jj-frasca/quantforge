"""Alpaca paper-broker adapter + reconcile (ADR-021).

A minimal REST client over Alpaca's free **paper** account (``paper-api.alpaca.markets`` — distinct
from the data host) that mirrors the OPEN paper book into real paper orders. The network glue is a
single injectable ``_fetch`` (``# pragma: no cover``) — the same pattern as
``app/data/sources/alpaca.py`` — so mapping + reconcile are unit-tested at 100% with a fake fetcher;
the real round-trip is a ``@pytest.mark.live`` smoke.

Paper only (CLAUDE.md rule 7): the constructor refuses any non-paper base URL, so a real-money
endpoint is structurally unreachable from this code path.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.execution.sizing import TargetPosition

Side = Literal["buy", "sell"]
Fetcher = Callable[[str, str, dict[str, Any] | None], Any]

_PAPER_HOST = "paper-api.alpaca.markets"


class AlpacaAccount(BaseModel):
    model_config = ConfigDict(frozen=True)

    equity: Decimal
    cash: Decimal
    buying_power: Decimal


class BrokerPosition(BaseModel):
    """A position as Alpaca reports it (may be fractional; reconcile manages whole shares)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    qty: Decimal
    market_value: Decimal
    avg_entry_price: Decimal


class AlpacaOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    symbol: str
    qty: int
    side: Side
    status: str


class AlpacaBroker:
    def __init__(
        self, base_url: str, api_key: str, secret_key: str, *, fetcher: Fetcher | None = None
    ) -> None:
        if _PAPER_HOST not in base_url:
            raise ValueError(
                f"AlpacaBroker is paper-only (rule 7): base_url must be the {_PAPER_HOST} host, "
                f"got {base_url!r}"
            )
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._secret_key = secret_key
        self._fetch = fetcher or self._request

    def account(self) -> AlpacaAccount:
        data = self._fetch("GET", "/v2/account", None)
        return AlpacaAccount(
            equity=Decimal(str(data["equity"])),
            cash=Decimal(str(data["cash"])),
            buying_power=Decimal(str(data["buying_power"])),
        )

    def positions(self) -> list[BrokerPosition]:
        data = self._fetch("GET", "/v2/positions", None)
        return [
            BrokerPosition(
                symbol=p["symbol"],
                qty=Decimal(str(p["qty"])),
                market_value=Decimal(str(p["market_value"])),
                avg_entry_price=Decimal(str(p["avg_entry_price"])),
            )
            for p in data
        ]

    def submit_order(self, symbol: str, qty: int, side: Side) -> AlpacaOrder:
        if qty <= 0:
            raise ValueError(f"qty must be a positive whole number of shares, got {qty}")
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
        body = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        data = self._fetch("POST", "/v2/orders", body)
        return AlpacaOrder(
            id=str(data["id"]),
            symbol=data["symbol"],
            qty=int(data["qty"]),
            side=data["side"],
            status=str(data["status"]),
        )

    def _request(  # pragma: no cover - network glue, exercised by the live test
        self, method: str, path: str, body: dict[str, Any] | None
    ) -> Any:
        import json
        import urllib.request

        headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
            "Content-Type": "application/json",
        }
        payload = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self._base_url + path, data=payload, headers=headers, method=method
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)


def reconcile(broker: AlpacaBroker, targets: list[TargetPosition]) -> list[AlpacaOrder]:
    """Diff Alpaca's current positions against ``targets`` and place the minimum orders to close the
    gap. Idempotent: at target → no orders. A sign flip through zero is split into close-then-reverse
    (Alpaca rejects a single equity order that crosses zero). Whole-share management; fractional dust
    from external activity is truncated toward zero.
    """
    held = {p.symbol: int(p.qty) for p in broker.positions()}
    wanted = {t.symbol: t.target_qty for t in targets}
    orders: list[AlpacaOrder] = []
    for symbol in sorted(held.keys() | wanted.keys()):
        current = held.get(symbol, 0)
        target = wanted.get(symbol, 0)
        if current == target:
            continue
        crosses_zero = current != 0 and target != 0 and (current > 0) != (target > 0)
        if crosses_zero:
            orders.append(
                broker.submit_order(symbol, abs(current), "sell" if current > 0 else "buy")
            )
            orders.append(broker.submit_order(symbol, abs(target), "buy" if target > 0 else "sell"))
        else:
            delta = target - current
            orders.append(broker.submit_order(symbol, abs(delta), "buy" if delta > 0 else "sell"))
    return orders
