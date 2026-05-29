"""FundamentalData model: nullable ratios never coerced to 0, negative income/PE allowed, market_cap must be > 0 when present, symbol normalization."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.data.models.fundamental_data import FundamentalData


def _fund(**overrides: object) -> FundamentalData:
    base: dict[str, object] = {
        "symbol": "AAPL",
        "report_date": date(2024, 3, 31),
        "source": "yfinance",
    }
    base.update(overrides)
    return FundamentalData(**base)  # type: ignore[arg-type]


def test_fundamental_data_minimal_constructs() -> None:
    f = _fund()
    assert f.symbol == "AAPL"
    assert f.report_date == date(2024, 3, 31)


def test_fundamental_data_missing_ratios_default_to_none_not_zero() -> None:
    f = _fund()
    assert f.pe_ratio is None
    assert f.pb_ratio is None
    assert f.market_cap is None


def test_fundamental_data_symbol_is_uppercased_and_stripped() -> None:
    assert _fund(symbol="  aapl ").symbol == "AAPL"


def test_fundamental_data_negative_net_income_is_allowed() -> None:
    assert _fund(net_income=Decimal("-1000")).net_income == Decimal("-1000")


def test_fundamental_data_negative_pe_ratio_is_allowed() -> None:
    # Negative earnings produce a negative P/E — a legitimate value, not an error.
    assert _fund(pe_ratio=Decimal("-5.2")).pe_ratio == Decimal("-5.2")


def test_fundamental_data_zero_market_cap_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _fund(market_cap=Decimal("0"))


def test_fundamental_data_negative_market_cap_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _fund(market_cap=Decimal("-1"))


def test_fundamental_data_positive_market_cap_is_accepted() -> None:
    assert _fund(market_cap=Decimal("2.5e12")).market_cap == Decimal("2.5e12")


def test_fundamental_data_empty_symbol_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _fund(symbol="   ")
