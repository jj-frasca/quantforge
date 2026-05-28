from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version

from app.data.models import PriceBar
from app.data.normalizers.ohlcv import OHLCVNormalizer, RawBar
from app.data.sources.base import DataSourceAdapter

Downloader = Callable[[str, datetime, datetime], list[RawBar]]


class YFinanceAdapter(DataSourceAdapter):
    """yfinance implementation of DataSourceAdapter — the primary source (no API key).

    The network/pandas glue is isolated in ``_download_yf`` so the normalization path is
    unit-testable without hitting the network; inject a ``downloader`` in tests.
    """

    source = "yfinance"
    adapter_version = f"yfinance-{version('yfinance')}"

    def __init__(
        self,
        normalizer: OHLCVNormalizer | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        self._normalizer = normalizer or OHLCVNormalizer()
        self._download = downloader or self._download_yf

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raw = self._download(symbol, start, end)
        return self._normalizer.normalize(raw, symbol, self.source)

    def _download_yf(
        self, symbol: str, start: datetime, end: datetime
    ) -> list[RawBar]:  # pragma: no cover - network/pandas glue, exercised by the live test
        import yfinance as yf  # type: ignore[import-untyped]

        frame = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False)
        raw: list[RawBar] = []
        for index, row in frame.iterrows():
            ts = index.to_pydatetime()
            ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)
            raw.append(
                RawBar(
                    timestamp=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    adj_close=float(row["Adj Close"]),
                    volume=int(row["Volume"]),
                )
            )
        return raw
