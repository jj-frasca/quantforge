"""SEC EDGAR fundamentals source (ADR-017). The HTTP glue is injectable so the CIK-resolution +
fetch orchestration is unit-tested without network; the real pull is a @pytest.mark.live test."""

from typing import Any

import pytest

from app.data.sources.edgar import SecEdgarFundamentalsSource

_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
}


def _facts() -> dict[str, Any]:
    row = {
        "val": 400_000,
        "fy": 2024,
        "fp": "FY",
        "form": "10-K",
        "accn": "a",
        "filed": "2025-02-01",
    }
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [row]}},
                "NetIncomeLoss": {"units": {"USD": [{**row, "val": 100_000}]}},
            }
        },
    }


def _fake_fetcher(calls: list[str]):
    def fetch(url: str) -> dict[str, Any]:
        calls.append(url)
        if "company_tickers" in url:
            return _TICKERS
        if "companyfacts" in url:
            return _facts()
        raise AssertionError(f"unexpected url {url}")

    return fetch


def _source(calls: list[str]) -> SecEdgarFundamentalsSource:
    return SecEdgarFundamentalsSource(
        user_agent="QuantForge test test@example.com", fetcher=_fake_fetcher(calls)
    )


def test_fetch_resolves_cik_and_returns_a_snapshot() -> None:
    calls: list[str] = []
    snap = _source(calls).fetch("AAPL")
    assert snap.symbol == "AAPL"
    assert snap.cik == 320193
    assert snap.revenue == 400_000
    # CIK is zero-padded to 10 digits in the companyfacts URL.
    assert any("CIK0000320193.json" in url for url in calls)


def test_fetch_is_case_insensitive_on_ticker() -> None:
    snap = _source([]).fetch("aapl")
    assert snap.cik == 320193


def test_unknown_ticker_raises() -> None:
    with pytest.raises(ValueError, match="CIK"):
        _source([]).fetch("NOPE")


def test_ticker_map_is_fetched_once_and_cached() -> None:
    calls: list[str] = []
    source = _source(calls)
    source.fetch("AAPL")
    source.fetch("MSFT")
    assert sum("company_tickers" in url for url in calls) == 1  # cached after first resolve


@pytest.mark.live
def test_live_edgar_fetch_for_a_real_symbol() -> None:
    source = SecEdgarFundamentalsSource(user_agent="QuantForge research jjfrasca10@gmail.com")
    snap = source.fetch("AAPL")
    assert snap.cik == 320193
    assert snap.revenue > 0
    assert snap.accession_number
    assert snap.source == "SEC EDGAR"
