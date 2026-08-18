"""ADR-029 Layer 3(c): the hard financial-distress screen — a business-quality safety rail that
blocks graduation regardless of technicals. Calibrated for HIGH PRECISION: a false veto kills a
real statistical edge, so only extreme, multi-signal distress (chronic operating weakness AND a
balance-sheet failure) trips it. Missing data never vetoes (conservative, like the ADR-017 fallback)."""

import pytest

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.distress import (
    DistressScreen,
    financial_distress,
    make_distress_provider,
)


def _year(fy: int, **overrides: float | None) -> AnnualFundamentals:
    base: dict[str, float | None] = {
        "fiscal_year": fy,
        "revenue": 1000.0,
        "net_income": 100.0,
        "total_assets": 2000.0,
        "total_current_assets": 800.0,
        "total_current_liabilities": 400.0,
        "operating_cash_flow": 150.0,
        "retained_earnings": 300.0,
        "total_equity": 1200.0,
    }
    base.update(overrides)
    return AnnualFundamentals(**base)  # type: ignore[arg-type]


def _history(*years: AnnualFundamentals) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="TEST",
        cik=1,
        entity_name="Test Corp",
        form="10-K",
        accession_number="0000000000-00-000000",
        source_url="https://www.sec.gov/",
        years=tuple(years),
    )


def test_healthy_company_is_not_distressed() -> None:
    screen = financial_distress(_history(_year(2024)))
    assert screen == DistressScreen(distressed=False, reasons=[])


def test_unprofitable_but_liquid_and_solvent_is_not_distressed() -> None:
    # A single bad year with a strong balance sheet is not hard distress (high-precision veto).
    screen = financial_distress(_history(_year(2024, net_income=-50.0, operating_cash_flow=-20.0)))
    assert not screen.distressed


def test_negative_equity_alone_is_not_distress() -> None:
    # Buyback-driven negative equity (MCD/SBUX/HD) with healthy operations must NOT be vetoed.
    screen = financial_distress(
        _history(_year(2024, total_equity=-500.0, retained_earnings=-100.0))
    )
    assert not screen.distressed  # profitable + cash-generative -> not distressed


def test_insolvent_and_unprofitable_and_cash_burning_is_distressed() -> None:
    screen = financial_distress(
        _history(
            _year(
                2024,
                net_income=-200.0,  # unprofitable
                operating_cash_flow=-100.0,  # burning cash
                total_equity=-300.0,  # liabilities exceed assets -> leverage > 1
            )
        )
    )
    assert screen.distressed
    assert any("negative net income" in r for r in screen.reasons)
    assert any("operating cash flow" in r for r in screen.reasons)
    assert any("negative equity" in r for r in screen.reasons)


def test_illiquid_and_unprofitable_and_cash_burning_is_distressed() -> None:
    screen = financial_distress(
        _history(
            _year(
                2024,
                net_income=-200.0,
                operating_cash_flow=-100.0,
                total_current_assets=100.0,  # current ratio 0.25 < 1
                total_current_liabilities=400.0,
                total_equity=1200.0,  # still solvent, but illiquid
            )
        )
    )
    assert screen.distressed
    assert any("current ratio" in r for r in screen.reasons)


def test_unprofitable_and_illiquid_but_cash_generative_is_not_distressed() -> None:
    # Positive operating cash flow means the business still self-funds -> not hard distress.
    screen = financial_distress(
        _history(
            _year(
                2024,
                net_income=-200.0,
                operating_cash_flow=50.0,  # still generating cash
                total_current_assets=100.0,
                total_current_liabilities=400.0,
            )
        )
    )
    assert not screen.distressed


def test_missing_data_never_vetoes() -> None:
    screen = financial_distress(
        _history(_year(2024, net_income=None, operating_cash_flow=None, total_equity=None))
    )
    assert not screen.distressed


def test_empty_history_never_vetoes() -> None:
    assert not financial_distress(_history()).distressed


# ---- make_distress_provider ----------------------------------------------------------------------


def test_provider_screens_a_fetched_history() -> None:
    distressed = _history(
        _year(2024, net_income=-200.0, operating_cash_flow=-100.0, total_equity=-300.0)
    )
    provider = make_distress_provider(lambda symbol: distressed)
    screen = provider("XXX")
    assert screen is not None and screen.distressed


@pytest.mark.parametrize("exc", [ValueError("no CIK"), KeyError("k"), OSError("edgar down")])
def test_provider_returns_none_when_history_lookup_fails(exc: Exception) -> None:
    def _raises(symbol: str) -> FundamentalsHistory:
        raise exc

    # An unscorable name (ETF / unmapped ticker / vendor hiccup) never vetoes -> None, not a crash.
    assert make_distress_provider(_raises)("XXX") is None
