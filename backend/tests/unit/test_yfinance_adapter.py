"""YFinanceAdapter: normalizes injected raw rows (no network), uppercases symbol, exposes source/version; plus a live yfinance fetch test (excluded from CI)."""

from datetime import UTC, datetime

import pytest

from app.data.models import PriceBar
from app.data.normalizers.ohlcv import RawBar
from app.data.sources.retry import RetryPolicy
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


def test_a_vendor_fetch_error_is_normalized_to_oserror() -> None:
    # Regression (prod 2026-08-18): yfinance raises YFRateLimitError (NOT an OSError) when the cloud
    # IP is rate-limited. The adapter must normalize ANY downloader error into OSError so the
    # resilient per-symbol hunt records + skips it instead of crashing the whole sharded run.
    class _YFRateLimitError(Exception):
        pass

    def _raises(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        raise _YFRateLimitError("Too Many Requests. Rate limited.")

    adapter = YFinanceAdapter(downloader=_raises)
    with pytest.raises(OSError, match="fetch failed"):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


def test_a_nonfinite_price_from_the_vendor_is_normalized_to_oserror() -> None:
    # Regression (found via the fundamental sweep, 2026-08-18): yfinance returns NaN prices for
    # partial/recent or delisted bars; the Decimal normalizer then raises decimal.InvalidOperation
    # (an ArithmeticError, NOT ValueError/OSError). Normalization runs INSIDE the adapter's guard,
    # so this crash-class becomes an OSError the resilient hunt records + skips — protecting BOTH
    # the price hunt and the fundamental sweep from one bad name taking down the whole run.
    def _nan_bar(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        return [
            RawBar(
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                open=10.0,
                high=float("nan"),
                low=9.0,
                close=9.5,
                adj_close=9.5,
                volume=100,
            )
        ]

    adapter = YFinanceAdapter(downloader=_nan_bar)
    with pytest.raises(OSError, match="fetch failed"):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


def test_an_oserror_from_the_downloader_passes_through_unchanged() -> None:
    # OSError is already the kind the hunt handles -> re-raised as-is, not double-wrapped.
    def _raises(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        raise OSError("no data for symbol")

    adapter = YFinanceAdapter(downloader=_raises)
    with pytest.raises(OSError, match="no data for symbol"):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


def test_adapter_retries_a_throttled_fetch_and_succeeds() -> None:
    # ADR-031: Yahoo throttles the shared cloud egress IP at the yfinance session bootstrap, so the
    # SAME transient failure hits every symbol until one call gets through. base_delay=0 keeps the
    # test instant; the backoff schedule itself is covered in test_source_retry.
    attempts: list[int] = []

    def flaky(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("Too Many Requests. Rate limited.")
        return _fake_download(symbol, start, end)

    adapter = YFinanceAdapter(downloader=flaky, retry=RetryPolicy(attempts=3, base_delay=0.0))
    bars = adapter.fetch_price_bars(
        "aapl", datetime(2024, 1, 2, tzinfo=UTC), datetime(2024, 1, 4, tzinfo=UTC)
    )
    assert len(bars) == 2
    assert len(attempts) == 3


def test_adapter_gives_up_after_the_configured_attempts() -> None:
    def always_throttled(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        raise OSError("Too Many Requests. Rate limited.")

    adapter = YFinanceAdapter(
        downloader=always_throttled, retry=RetryPolicy(attempts=2, base_delay=0.0)
    )
    with pytest.raises(OSError, match="Rate limited"):
        adapter.fetch_price_bars(
            "aapl", datetime(2024, 1, 2, tzinfo=UTC), datetime(2024, 1, 4, tzinfo=UTC)
        )


def test_adapter_does_not_retry_a_vendor_exception_that_normalizes_to_a_data_verdict() -> None:
    # A malformed bar makes the normalizer raise ValueError — retrying re-parses the same bad bytes.
    attempts: list[int] = []

    def bad_data(symbol: str, start: datetime, end: datetime) -> list[RawBar]:
        attempts.append(1)
        raise ValueError("high < low")

    adapter = YFinanceAdapter(downloader=bad_data, retry=RetryPolicy(attempts=5, base_delay=0.0))
    with pytest.raises(ValueError, match="high < low"):
        adapter.fetch_price_bars(
            "aapl", datetime(2024, 1, 2, tzinfo=UTC), datetime(2024, 1, 4, tzinfo=UTC)
        )
    assert len(attempts) == 1
