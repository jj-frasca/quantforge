from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, ClassVar

from app.data.models.price_bar import PriceBar
from app.data.models.types import Source
from app.data.normalizers.ohlcv import OHLCVNormalizer, RawBar
from app.data.sources.base import DataSourceAdapter

BarFetcher = Callable[[str, datetime, datetime], list[dict[str, Any]]]

_DATA_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"


class AlpacaDataAdapter(DataSourceAdapter):
    """Alpaca daily-bar data adapter (ADR-019). Chosen for cloud reliability — yfinance is flaky
    from cloud IPs, and Alpaca's free tier is designed for programmatic access.

    Bars are requested split/dividend-adjusted (``adjustment=all``); we set ``close == adj_close``
    since Alpaca returns the already-adjusted series (returns-based backtests want adjusted prices).
    The network/pagination glue is isolated in ``_fetch_bars`` (injectable) so mapping +
    normalization are unit-testable without the network — same pattern as YFinanceAdapter.
    """

    source: ClassVar[Source] = "alpaca"
    adapter_version: ClassVar[str] = "alpaca-data-v2"

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        normalizer: OHLCVNormalizer | None = None,
        fetcher: BarFetcher | None = None,
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._normalizer = normalizer or OHLCVNormalizer()
        self._fetch = fetcher or self._fetch_bars

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raw_bars = self._fetch(symbol, start, end)
        raw = [
            RawBar(
                timestamp=_parse_ts(bar["t"]),
                open=float(bar["o"]),
                high=float(bar["h"]),
                low=float(bar["l"]),
                close=float(bar["c"]),
                adj_close=float(bar["c"]),
                volume=int(bar["v"]),
            )
            for bar in raw_bars
        ]
        return self._normalizer.normalize(raw, symbol, self.source)

    def _fetch_bars(  # pragma: no cover - network/pagination glue, exercised by the live test
        self, symbol: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        import json
        import urllib.parse
        import urllib.request

        headers = {"APCA-API-KEY-ID": self._api_key, "APCA-API-SECRET-KEY": self._secret_key}
        bars: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {
                "timeframe": "1Day",
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                "adjustment": "all",
                "limit": "10000",
            }
            if page_token:
                params["page_token"] = page_token
            url = _DATA_URL.format(symbol=symbol) + "?" + urllib.parse.urlencode(params)
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                payload: dict[str, Any] = json.load(response)
            bars.extend(payload.get("bars") or [])
            page_token = payload.get("next_page_token")
            if not page_token:
                return bars


def _parse_ts(raw: str) -> datetime:
    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return ts.astimezone(UTC)
