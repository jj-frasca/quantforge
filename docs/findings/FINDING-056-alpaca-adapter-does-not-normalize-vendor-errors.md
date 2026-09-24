# FINDING-056: Alpaca adapter never normalized vendor errors to `OSError`

- **Severity:** Low
- **Status:** Resolved by ADR-128
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/data/sources/
  {alpaca,base}.py`)
- **Affects:** `AlpacaDataAdapter.fetch_price_bars` (`app/data/sources/alpaca.py`)

## Finding

`AlpacaDataAdapter`'s own docstring states: "The network/pagination glue is isolated in
`_fetch_bars`... same pattern as YFinanceAdapter." `YFinanceAdapter._fetch_once` wraps any
vendor-specific fetch or parse error that isn't already `ValueError`/`KeyError`/`OSError` into a
plain `OSError` — a guard added after two real production incidents (2026-08-18): yfinance raises
`YFRateLimitError` (not an `OSError`) on cloud-IP rate limiting, and a NaN price from a partial/
delisted bar makes the Decimal normalizer raise `decimal.InvalidOperation` (an `ArithmeticError`).
Both took down sharded runs before the guard existed.

`AlpacaDataAdapter.fetch_price_bars` had no such guard — no `try`/`except` at all. Any
vendor-specific exception (an `HTTPError` from `urllib`, a `json.JSONDecodeError`, or any other
non-`(ValueError, KeyError, OSError)` failure) would propagate as-is, not the normalized `OSError`
the docstring claims and the rest of this codebase's error-handling convention expects.

Lower severity than a typical "crashes the hunt" finding: `AlpacaDataAdapter` is constructed only
via `app/dependencies.py`'s FastAPI dependency injection (used by the `/ingest`, `/bars`,
`/backtest`, `/validate` routes when Alpaca keys are configured) — it is not used by the sharded
discovery/hunt scripts (those use `YFinanceAdapter`), so the specific "crashes a whole sharded run"
failure mode this guard exists to prevent doesn't apply here. The real, narrower impact: an
unhandled vendor-specific exception surfaces as a generic FastAPI 500 with a raw urllib/json
exception message instead of a clean, consistently-typed `OSError`, and the docstring's claim was
simply false.

## Reproduction

```python
from app.data.sources.alpaca import AlpacaDataAdapter
from datetime import datetime, UTC

class _AlpacaRateLimitError(Exception):
    pass

def raises(symbol, start, end):
    raise _AlpacaRateLimitError("429 Too Many Requests")

adapter = AlpacaDataAdapter("key", "secret", fetcher=raises)
adapter.fetch_price_bars("AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC))
# pre-fix: raises _AlpacaRateLimitError, not OSError
```
