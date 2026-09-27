"""Scheduled paper-broker step (ADR-021): wire the OPEN managed book into real Alpaca paper orders.

The pure orchestration — open positions + a frame-provider + equity → signed whole-share targets —
is network-free and unit-tested at 100% over synthetic frames. The real HTTP round-trip (account +
reconcile against the free paper account) is a @pytest.mark.live smoke that SKIPS without keys.
Paper only (rule 7)."""

import os
from datetime import UTC, datetime

import pandas as pd
import pytest
from scripts.paper_broker import PAPER_URL, compute_targets

from app.data.models import DataQualityReport
from app.execution.alpaca_broker import AlpacaBroker, reconcile
from app.execution.sizing import TargetPosition
from app.research.dataset import ResearchDataset
from app.research.lab.paper import PaperPosition


def _position(symbol: str) -> PaperPosition:
    return PaperPosition(
        symbol=symbol,
        strategy_name="sma",
        parameters={"fast": 2, "slow": 4},
        frozen_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _uptrend_frame() -> pd.DataFrame:
    # SMA(2,4): trailing fast mean > slow mean on the last bar → long (+1).
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.DataFrame({"close": [1.0, 2, 3, 4, 5, 6, 7, 8]}, index=idx)


def _downtrend_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.DataFrame({"close": [8.0, 7, 6, 5, 4, 3, 2, 1]}, index=idx)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame({"close": pd.Series(dtype="float64")}, index=pd.DatetimeIndex([], tz="UTC"))


def _dataset(symbol: str, frame: pd.DataFrame) -> ResearchDataset:
    aware = frame.copy()
    if aware.index.tz is None:
        aware.index = aware.index.tz_localize("UTC")
    return ResearchDataset(
        frame=aware,
        quality_report=DataQualityReport(
            symbol=symbol, source="yfinance", checked_at=datetime(2024, 1, 9, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="test-1",
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 9, tzinfo=UTC),
        git_commit_hash="a" * 40,
    )


def test_compute_targets_equal_weights_open_positions() -> None:
    frames = {"AAPL": _uptrend_frame(), "MSFT": _uptrend_frame()}
    targets = compute_targets(
        [_position("AAPL"), _position("MSFT")],
        lambda s: _dataset(s, frames[s]),
        equity=100_000.0,
    )
    # Two active longs, last close 8.0 each: 50k slice / 8 = 6250 shares apiece.
    assert {t.symbol: t.target_qty for t in targets} == {"AAPL": 6250, "MSFT": 6250}


def test_compute_targets_signs_short_positions() -> None:
    targets = compute_targets(
        [_position("AAPL")],
        lambda s: _dataset(s, _downtrend_frame()),
        equity=100_000.0,
    )
    # Single short at last close 1.0: full equity slice * -1 / 1.0 = -100000 shares.
    assert targets[0].symbol == "AAPL"
    assert targets[0].target_qty == -100_000


def test_compute_targets_skips_positions_with_no_bars() -> None:
    def provider(symbol: str) -> ResearchDataset:
        if symbol == "MSFT":
            raise ValueError("quality report failed for MSFT: insufficient_data")
        return _dataset(symbol, _uptrend_frame())

    targets = compute_targets([_position("AAPL"), _position("MSFT")], provider, equity=100_000.0)
    # MSFT has no fresh bars → no quote; AAPL takes the whole book (100k / 8 = 12500).
    assert {t.symbol: t.target_qty for t in targets} == {"AAPL": 12500}


def test_compute_targets_empty_book_is_no_targets() -> None:
    assert compute_targets([], lambda _s: _uptrend_frame(), equity=100_000.0) == []


def test_compute_targets_uses_provider_per_symbol() -> None:
    seen: list[str] = []

    def provider(symbol: str) -> ResearchDataset:
        seen.append(symbol)
        return _dataset(symbol, _uptrend_frame())

    compute_targets([_position("AAPL"), _position("MSFT")], provider, equity=1_000.0)
    assert seen == ["AAPL", "MSFT"]


def test_compute_targets_accepts_only_quality_checked_datasets() -> None:
    with pytest.raises(TypeError, match="ResearchDataset"):
        compute_targets([_position("AAPL")], lambda _symbol: _uptrend_frame(), equity=1_000.0)


def test_compute_targets_sizes_from_quality_checked_dataset_frame() -> None:
    targets = compute_targets(
        [_position("AAPL")],
        lambda symbol: _dataset(symbol, _uptrend_frame()),
        equity=1_000.0,
    )

    assert targets[0].symbol == "AAPL"
    assert targets[0].target_qty == 125


def test_compute_targets_skips_a_dataset_fetch_or_quality_failure() -> None:
    def provider(symbol: str) -> ResearchDataset:
        if symbol == "MSFT":
            raise ValueError("quality report failed for MSFT: source_mismatch")
        return _dataset(symbol, _uptrend_frame())

    targets = compute_targets([_position("AAPL"), _position("MSFT")], provider, equity=1_000.0)

    assert [target.symbol for target in targets] == ["AAPL"]


def test_compute_targets_skips_dataset_for_a_different_symbol() -> None:
    targets = compute_targets(
        [_position("AAPL")],
        lambda _symbol: _dataset("MSFT", _uptrend_frame()),
        equity=1_000.0,
    )

    assert targets == []


def test_paper_url_is_the_paper_host() -> None:
    assert PAPER_URL == "https://paper-api.alpaca.markets"


@pytest.mark.live
def test_live_reconcile_places_paper_orders() -> None:
    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        pytest.skip("ALPACA_API_KEY / ALPACA_SECRET_KEY not set")
    broker = AlpacaBroker(PAPER_URL, key, secret)
    equity = float(broker.account().equity)
    assert equity > 0
    # Idempotent: reconcile to the currently-held book places no orders on a repeat run.
    targets = [TargetPosition(symbol=p.symbol, target_qty=int(p.qty)) for p in broker.positions()]
    assert reconcile(broker, targets) == []
