"""Real Alpaca paper-broker adapter + reconcile (ADR-021). The HTTP glue is injectable so account/
positions/order mapping and the reconcile diff are unit-tested at 100% without network; the real
round-trip is a @pytest.mark.live smoke against the free paper account. Paper only (rule 7)."""

import os
from decimal import Decimal
from typing import Any

import pytest

from app.execution.alpaca_broker import (
    AlpacaAccount,
    AlpacaBroker,
    AlpacaOrder,
    BrokerPosition,
    reconcile,
)
from app.execution.sizing import TargetPosition

_PAPER_URL = "https://paper-api.alpaca.markets"

_ACCOUNT = {"equity": "100000.00", "cash": "100000.00", "buying_power": "200000.00"}


class FakeAlpaca:
    """Routes (method, path) to canned Alpaca JSON and records submitted orders."""

    def __init__(self, positions: list[dict[str, Any]] | None = None) -> None:
        self._positions = positions or []
        self.orders: list[dict[str, Any]] = []
        self._order_id = 0

    def __call__(self, method: str, path: str, body: dict[str, Any] | None) -> Any:
        if method == "GET" and path == "/v2/account":
            return _ACCOUNT
        if method == "GET" and path == "/v2/positions":
            return self._positions
        if method == "POST" and path == "/v2/orders":
            assert body is not None
            self.orders.append(body)
            self._order_id += 1
            return {
                "id": f"order-{self._order_id}",
                "symbol": body["symbol"],
                "qty": body["qty"],
                "side": body["side"],
                "status": "accepted",
            }
        raise AssertionError(f"unexpected call {method} {path}")


def _pos(symbol: str, qty: str, price: str = "100.00") -> dict[str, Any]:
    return {
        "symbol": symbol,
        "qty": qty,
        "market_value": str(Decimal(qty) * Decimal(price)),
        "avg_entry_price": price,
    }


def _broker(positions: list[dict[str, Any]] | None = None) -> tuple[AlpacaBroker, FakeAlpaca]:
    fake = FakeAlpaca(positions)
    return AlpacaBroker(_PAPER_URL, "key", "secret", fetcher=fake), fake


# --- constructor guard ---


def test_rejects_non_paper_base_url() -> None:
    with pytest.raises(ValueError, match="paper"):
        AlpacaBroker("https://api.alpaca.markets", "key", "secret", fetcher=FakeAlpaca())


def test_accepts_paper_base_url() -> None:
    broker, _ = _broker()
    assert isinstance(broker, AlpacaBroker)


# --- account / positions / submit_order mapping ---


def test_account_maps_alpaca_fields_to_decimals() -> None:
    broker, _ = _broker()
    account = broker.account()
    assert account == AlpacaAccount(
        equity=Decimal("100000.00"),
        cash=Decimal("100000.00"),
        buying_power=Decimal("200000.00"),
    )


def test_positions_maps_alpaca_fields() -> None:
    broker, _ = _broker([_pos("AAPL", "50", "150.00")])
    positions = broker.positions()
    assert positions == [
        BrokerPosition(
            symbol="AAPL",
            qty=Decimal("50"),
            market_value=Decimal("7500.00"),
            avg_entry_price=Decimal("150.00"),
        )
    ]


def test_no_positions_is_empty_list() -> None:
    broker, _ = _broker([])
    assert broker.positions() == []


def test_submit_order_posts_market_day_order_and_maps_response() -> None:
    broker, fake = _broker()
    order = broker.submit_order("AAPL", 10, "buy")
    assert fake.orders == [
        {"symbol": "AAPL", "qty": "10", "side": "buy", "type": "market", "time_in_force": "day"}
    ]
    assert order == AlpacaOrder(id="order-1", symbol="AAPL", qty=10, side="buy", status="accepted")


def test_submit_order_rejects_nonpositive_qty() -> None:
    broker, _ = _broker()
    with pytest.raises(ValueError, match="qty"):
        broker.submit_order("AAPL", 0, "buy")


def test_submit_order_rejects_unknown_side() -> None:
    broker, _ = _broker()
    with pytest.raises(ValueError, match="side"):
        broker.submit_order("AAPL", 1, "hold")  # type: ignore[arg-type]


# --- reconcile diff logic ---


def test_reconcile_opens_new_long() -> None:
    broker, fake = _broker([])
    orders = reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=50)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [("AAPL", "50", "buy")]
    assert len(orders) == 1


def test_reconcile_is_idempotent_when_already_at_target() -> None:
    broker, fake = _broker([_pos("AAPL", "50")])
    orders = reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=50)])
    assert fake.orders == []
    assert orders == []


def test_reconcile_increases_a_position() -> None:
    broker, fake = _broker([_pos("AAPL", "30")])
    reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=50)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [("AAPL", "20", "buy")]


def test_reconcile_reduces_a_position() -> None:
    broker, fake = _broker([_pos("AAPL", "50")])
    reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=30)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [("AAPL", "20", "sell")]


def test_reconcile_flattens_a_held_name_absent_from_targets() -> None:
    broker, fake = _broker([_pos("AAPL", "40")])
    reconcile(broker, [])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [("AAPL", "40", "sell")]


def test_reconcile_flattens_on_explicit_zero_target() -> None:
    broker, fake = _broker([_pos("AAPL", "40")])
    reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=0)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [("AAPL", "40", "sell")]


def test_reconcile_splits_long_to_short_into_close_then_reverse() -> None:
    broker, fake = _broker([_pos("AAPL", "50")])
    reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=-10)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [
        ("AAPL", "50", "sell"),  # close the long
        ("AAPL", "10", "sell"),  # open the short
    ]


def test_reconcile_splits_short_to_long_into_close_then_reverse() -> None:
    broker, fake = _broker([_pos("AAPL", "-20")])
    reconcile(broker, [TargetPosition(symbol="AAPL", target_qty=30)])
    assert [(o["symbol"], o["qty"], o["side"]) for o in fake.orders] == [
        ("AAPL", "20", "buy"),  # close the short
        ("AAPL", "30", "buy"),  # open the long
    ]


def test_reconcile_handles_multiple_names_deterministically() -> None:
    broker, fake = _broker([_pos("AAPL", "10"), _pos("SPY", "5")])
    reconcile(
        broker,
        [
            TargetPosition(symbol="AAPL", target_qty=10),  # unchanged → no order
            TargetPosition(symbol="SPY", target_qty=8),  # buy 3
            TargetPosition(symbol="MSFT", target_qty=4),  # new → buy 4
        ],
    )
    assert sorted((o["symbol"], o["qty"], o["side"]) for o in fake.orders) == [
        ("MSFT", "4", "buy"),
        ("SPY", "3", "buy"),
    ]


# --- live smoke (excluded from CI) ---


@pytest.mark.live
def test_live_paper_account_and_order() -> None:
    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        pytest.skip("ALPACA_API_KEY / ALPACA_SECRET_KEY not set")
    broker = AlpacaBroker(_PAPER_URL, key, secret)
    account = broker.account()
    assert account.equity > 0
    order = broker.submit_order("AAPL", 1, "buy")
    assert order.symbol == "AAPL"
    assert order.status
