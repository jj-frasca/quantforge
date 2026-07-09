from collections.abc import Callable
from typing import Any

from app.data.fundamentals import (
    FundamentalsHistory,
    FundamentalSnapshot,
    parse_company_facts,
    parse_company_facts_history,
)

JsonFetcher = Callable[[str], dict[str, Any]]

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


class SecEdgarFundamentalsSource:
    """Fetches citation-backed fundamentals from SEC EDGAR (ADR-017).

    The HTTP glue is isolated in ``_http_get_json`` (injectable) so CIK resolution + fetch
    orchestration are unit-testable without the network. EDGAR requires a descriptive
    ``User-Agent`` and asks for <= 10 req/s. The ticker->CIK map is fetched once per instance.
    """

    source = "SEC EDGAR"

    def __init__(self, user_agent: str, fetcher: JsonFetcher | None = None) -> None:
        self._user_agent = user_agent
        self._fetch_json = fetcher or self._http_get_json
        self._ticker_to_cik: dict[str, int] | None = None

    def fetch(self, symbol: str) -> FundamentalSnapshot:
        cik = self._cik_for(symbol)
        facts = self._fetch_json(_COMPANY_FACTS_URL.format(cik=cik))
        return parse_company_facts(facts, symbol.upper())

    def fetch_history(self, symbol: str) -> FundamentalsHistory:
        """Multi-year fundamentals for a symbol (ADR-022), for valuation-vs-own-history + DCF."""
        cik = self._cik_for(symbol)
        facts = self._fetch_json(_COMPANY_FACTS_URL.format(cik=cik))
        return parse_company_facts_history(facts, symbol.upper())

    def _cik_for(self, symbol: str) -> int:
        if self._ticker_to_cik is None:
            mapping = self._fetch_json(_TICKERS_URL)
            self._ticker_to_cik = {
                str(entry["ticker"]).upper(): int(entry["cik_str"]) for entry in mapping.values()
            }
        cik = self._ticker_to_cik.get(symbol.upper())
        if cik is None:
            raise ValueError(f"no CIK found for ticker {symbol!r} in SEC ticker map")
        return cik

    def _http_get_json(
        self, url: str
    ) -> dict[str, Any]:  # pragma: no cover - network glue, live test
        import json
        import urllib.request

        request = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        with urllib.request.urlopen(request, timeout=30) as response:
            data: dict[str, Any] = json.load(response)
        return data
