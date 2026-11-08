"""ADR418 one final-window entry point. No overrides, retries or current execution."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.research.cross_sectional.prospective_portfolio import (
    ROOT,
    Provider,
    _evaluate,
    check_window,
    prepare,
)

REPO = Path(__file__).resolve().parents[2]


def utc_now() -> datetime:
    return datetime.now(UTC)


def main() -> None:
    check_window(utc_now())
    prepared = prepare(REPO)

    def provider_factory() -> Provider:
        from app.data.sources.yfinance import YFinanceAdapter

        adapter = YFinanceAdapter()
        return adapter.fetch_price_bars

    result = _evaluate(prepared, ROOT, provider_factory=provider_factory, clock=utc_now)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
