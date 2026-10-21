"""Initial broker-origin allowlist (ADR-341); no external transport or credentials."""

import io
import urllib.request
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.execution.alpaca_broker import AlpacaBroker

PAPER = "https://paper-api.alpaca.markets"


def _forbidden_fetch(*args: object) -> None:
    pytest.fail("constructor must not call the injected transport")


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.alpaca.markets/v2/orders#paper-api.alpaca.markets",
        "https://paper-api.alpaca.markets@api.alpaca.markets",
        "https://paper-api.alpaca.markets.invalid",
        "https://prefix.paper-api.alpaca.markets",
        "https://invalid.test/paper-api.alpaca.markets",
        "https://invalid.test/?paper-api.alpaca.markets",
        "https://invalid.test/#paper-api.alpaca.markets",
        "http://paper-api.alpaca.markets",
        PAPER + ":443",
        PAPER + ":80",
        PAPER + ".",
        PAPER + "/v2",
        PAPER + "/v2/orders",
        PAPER + "?",
        PAPER + "?mode=paper",
        PAPER + "#",
        PAPER + "#paper",
        "https://user:synthetic@paper-api.alpaca.markets",
        "https://@paper-api.alpaca.markets",
        "file:///paper-api.alpaca.markets",
        "paper-api.alpaca.markets",
        "https://api.alpaca.markets",
        "https://PAPER-API.ALPACA.MARKETS",
    ],
)
def test_alpaca_broker_noncanonical_origin_refuses_before_transport(base_url: str) -> None:
    with pytest.raises(ValueError, match="paper-only"):
        AlpacaBroker(base_url, "synthetic-key", "synthetic-secret", fetcher=_forbidden_fetch)


@pytest.mark.parametrize("suffix", ["", "/", "///"])
def test_alpaca_broker_canonical_origin_preserves_injected_transport(suffix: str) -> None:
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def fetch(method: str, path: str, body: dict[str, Any] | None) -> dict[str, str]:
        calls.append((method, path, body))
        return {"equity": "1000", "cash": "1000", "buying_power": "1000"}

    broker = AlpacaBroker(PAPER + suffix, "synthetic-key", "synthetic-secret", fetcher=fetch)
    assert broker.account().equity == 1000
    assert calls == [("GET", "/v2/account", None)]


@pytest.mark.parametrize("suffix", ["", "/", "///"])
def test_alpaca_broker_canonical_initial_request_has_paper_authority(
    suffix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[tuple[str, str, str]] = []

    def intercepted(
        opener: urllib.request.OpenerDirector,
        request: urllib.request.Request,
        data: bytes | None = None,
        timeout: int = 30,
    ) -> io.BytesIO:
        captured.append((request.host, request.selector, request.get_method()))
        assert data is None
        assert timeout == 30
        return io.BytesIO(
            b'{"id":"synthetic","symbol":"SYNTH","qty":"1","side":"buy","status":"new"}'
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", intercepted)
    broker = AlpacaBroker(PAPER + suffix, "synthetic-key", "synthetic-secret")
    assert broker.submit_order("SYNTH", 1, "buy").id == "synthetic"
    assert captured == [("paper-api.alpaca.markets", "/v2/orders", "POST")]


@given(label=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=40))
def test_alpaca_broker_paper_hostname_inside_other_authority_never_passes(label: str) -> None:
    base_url = f"https://paper-api.alpaca.markets.{label}.invalid"
    with pytest.raises(ValueError, match="paper-only"):
        AlpacaBroker(base_url, "synthetic-key", "synthetic-secret", fetcher=_forbidden_fetch)
