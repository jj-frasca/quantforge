"""YFinanceAdapter: normalizes injected raw rows (no network), uppercases symbol, exposes source/version; plus a live yfinance fetch test (excluded from CI)."""

from datetime import UTC, datetime

import pytest

from app.data.models import PriceBar
from app.data.normalizers.ohlcv import RawBar
from app.data.sources.yfinance import YFinanceAdapter


def _fake_download(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
    return [
        RawBar(
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=100.0,
            high=110.0,
            low=95.0,
            close=100.0,
            adj_close=100.0,
            volume=1000,
        ),
        RawBar(
            timestamp=datetime(2024, 1, 3, tzinfo=UTC),
            open=101.0,
            high=112.0,
            low=99.0,
            close=105.0,
            adj_close=105.0,
            volume=1200,
        ),
    ]


def test_yfinance_adapter_normalizes_downloaded_rows() -> None:
    adapter = YFinanceAdapter(downloader=_fake_download)
    bars = adapter.fetch_price_bars(
        "aapl", datetime(2024, 1, 2, tzinfo=UTC), datetime(2024, 1, 4, tzinfo=UTC)
    )
    assert len(bars) == 2
    assert all(isinstance(b, PriceBar) for b in bars)
    assert all(b.symbol == "AAPL" for b in bars)
    assert all(b.source == "yfinance" for b in bars)


def test_yfinance_adapter_exposes_source_and_version() -> None:
    adapter = YFinanceAdapter(downloader=_fake_download)
    assert adapter.source == "yfinance"
    assert adapter.adapter_version.startswith("yfinance-")


@pytest.mark.live
def test_yfinance_adapter_fetches_real_bars() -> None:
    adapter = YFinanceAdapter()
    bars = adapter.fetch_price_bars(
        "AAPL", datetime(2024, 1, 2, tzinfo=UTC), datetime(2024, 1, 10, tzinfo=UTC)
    )
    assert len(bars) > 0
    assert all(b.symbol == "AAPL" for b in bars)
