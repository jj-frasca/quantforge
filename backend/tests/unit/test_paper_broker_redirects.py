"""Authenticated default broker transport refuses redirects (ADR-342); HTTP is blocked."""

import io
import json
import urllib.request
from http.client import HTTPMessage
from typing import Any
from urllib.error import HTTPError
from urllib.response import addinfourl

import pytest

from app.execution.alpaca_broker import AlpacaBroker

PAPER = "https://paper-api.alpaca.markets"


class _FakeHTTPS(urllib.request.HTTPSHandler):
    def __init__(self, code: int, destination: str) -> None:
        super().__init__()
        self.code = code
        self.destination = destination
        self.calls: list[urllib.request.Request] = []

    def https_open(self, request: urllib.request.Request) -> Any:
        self.calls.append(request)
        assert len(self.calls) == 1, "redirect attempted a follow-up transport"
        headers = HTTPMessage()
        headers["Location"] = self.destination
        response = addinfourl(
            io.BytesIO(b'{"synthetic":true}'), headers, request.full_url, self.code
        )
        response.msg = "synthetic response"
        return response


@pytest.fixture
def fake_transport(monkeypatch: pytest.MonkeyPatch) -> Any:
    original_build = urllib.request.build_opener

    def forbidden_http(*args: object, **kwargs: object) -> None:
        pytest.fail("real HTTP transport is forbidden")

    # Even a broken opener hookup must fail before any real HTTP/TLS transport.
    monkeypatch.setattr(urllib.request.AbstractHTTPHandler, "do_open", forbidden_http)
    monkeypatch.setattr(urllib.request, "_opener", None)

    def configure(code: int, destination: str = PAPER + "/redirect") -> _FakeHTTPS:
        fake = _FakeHTTPS(code, destination)

        def build(*handlers: Any) -> urllib.request.OpenerDirector:
            return original_build(urllib.request.ProxyHandler({}), fake, *handlers)

        monkeypatch.setattr(urllib.request, "build_opener", build)
        return fake

    return configure


def _assert_initial_request(request: urllib.request.Request, method: str) -> None:
    path = "/v2/orders" if method == "POST" else "/v2/account"
    assert request.full_url == PAPER + path
    assert request.get_method() == method
    assert request.timeout == 30
    assert dict(request.header_items())["Apca-api-key-id"] == "synthetic-key"
    assert dict(request.header_items())["Apca-api-secret-key"] == "synthetic-secret"
    assert request.get_header("Content-type") == "application/json"
    if method == "POST":
        assert request.data == json.dumps({"synthetic": True}).encode()
    else:
        assert request.data is None


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("destination", [PAPER + "/redirect", "https://other.invalid/redirect"])
def test_paper_broker_redirect_refuses_before_followup_with_native_error(
    method: str, code: int, destination: str, fake_transport: Any
) -> None:
    fake = fake_transport(code, destination)
    broker = AlpacaBroker(PAPER, "synthetic-key", "synthetic-secret")
    path = "/v2/orders" if method == "POST" else "/v2/account"
    body = {"synthetic": True} if method == "POST" else None
    with pytest.raises(HTTPError) as error:
        broker._request(method, path, body)
    assert error.value.code == code
    assert error.value.url == PAPER + path
    assert error.value.read() == b'{"synthetic":true}'
    error.value.close()
    assert len(fake.calls) == 1
    _assert_initial_request(fake.calls[0], method)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_paper_broker_nonredirect_json_preserves_request(method: str, fake_transport: Any) -> None:
    fake = fake_transport(200)
    broker = AlpacaBroker(PAPER, "synthetic-key", "synthetic-secret")
    path = "/v2/orders" if method == "POST" else "/v2/account"
    body = {"synthetic": True} if method == "POST" else None
    assert broker._request(method, path, body) == {"synthetic": True}
    assert len(fake.calls) == 1
    _assert_initial_request(fake.calls[0], method)


@pytest.mark.parametrize("code", [300, 304, 400, 503])
def test_paper_broker_other_http_errors_preserve_status_and_body(
    code: int, fake_transport: Any
) -> None:
    fake = fake_transport(code)
    broker = AlpacaBroker(PAPER, "synthetic-key", "synthetic-secret")
    with pytest.raises(HTTPError) as error:
        broker._request("GET", "/v2/account", None)
    assert error.value.code == code
    assert error.value.read() == b'{"synthetic":true}'
    error.value.close()
    assert len(fake.calls) == 1


def test_paper_broker_local_transport_bypasses_global_custom_opener(
    fake_transport: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = fake_transport(200)

    class GlobalOpener:
        def open(self, *args: object, **kwargs: object) -> None:
            pytest.fail("global custom opener must not replace the broker redirect policy")

    monkeypatch.setattr(urllib.request, "_opener", GlobalOpener())
    broker = AlpacaBroker(PAPER, "synthetic-key", "synthetic-secret")
    assert broker._request("GET", "/v2/account", None) == {"synthetic": True}
    assert len(fake.calls) == 1
