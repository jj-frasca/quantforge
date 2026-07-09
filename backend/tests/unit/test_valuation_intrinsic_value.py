"""FCFE DCF intrinsic value from a FundamentalsHistory (ADR-022). Assumption-driven and honest:
every fallback is flagged, and the assumptions are recorded on the result. Pure + deterministic."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.valuation.intrinsic_value import (
    DcfAssumptions,
    IntrinsicValueResult,
    dcf_intrinsic_value,
    estimate_growth,
)


def _history(years: list[AnnualFundamentals]) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="AAPL",
        cik=320193,
        entity_name="Apple Inc.",
        form="10-K",
        accession_number="a-2024",
        source_url="https://sec.gov/x",
        years=tuple(years),
    )


def _year(fy: int, **kw: float) -> AnnualFundamentals:
    return AnnualFundamentals(fiscal_year=fy, revenue=kw.pop("revenue", 100.0), **kw)


# A flat-growth DCF collapses to a perpetuity: FCF / r. With FCF=12, r=0.10, shares=100 the
# intrinsic value is 12/0.10/100 = 1.2 — an oracle independent of the projection loop.
_FLAT = DcfAssumptions(
    discount_rate=0.10, terminal_growth=0.0, projection_years=2, max_growth=0.0, min_growth=0.0
)


def test_flat_growth_dcf_equals_perpetuity_per_share() -> None:
    hist = _history(
        [
            _year(2023, free_cash_flow=10.0, shares_diluted=100.0, net_income=8.0),
            _year(2024, free_cash_flow=12.0, shares_diluted=100.0, net_income=9.0),
        ]
    )
    result = dcf_intrinsic_value(hist, _FLAT)
    assert isinstance(result, IntrinsicValueResult)
    assert result.intrinsic_value_per_share == pytest.approx(1.2)
    assert result.growth_rate_used == 0.0
    assert result.fcf_base == 12.0
    assert result.fcf_is_net_income_proxy is False
    assert result.assumptions == _FLAT
    assert result.flags == []


def test_uses_net_income_as_flagged_proxy_when_fcf_absent() -> None:
    hist = _history(
        [
            _year(2023, net_income=10.0, shares_diluted=100.0),
            _year(2024, net_income=12.0, shares_diluted=100.0),
        ]
    )
    result = dcf_intrinsic_value(hist, _FLAT)
    assert result.fcf_base == 12.0
    assert result.fcf_is_net_income_proxy is True
    assert result.intrinsic_value_per_share == pytest.approx(1.2)
    assert any("net income" in f.lower() for f in result.flags)


def test_growth_is_clamped_to_max() -> None:
    # FCF 10 -> 20 is 100% CAGR; clamp to max_growth.
    hist = _history(
        [
            _year(2023, free_cash_flow=10.0, shares_diluted=100.0),
            _year(2024, free_cash_flow=20.0, shares_diluted=100.0),
        ]
    )
    result = dcf_intrinsic_value(hist, DcfAssumptions(max_growth=0.12))
    assert result.growth_rate_used == 0.12


def test_non_positive_base_cash_flow_is_not_valued() -> None:
    hist = _history(
        [
            _year(2023, free_cash_flow=-5.0, shares_diluted=100.0),
            _year(2024, free_cash_flow=-8.0, shares_diluted=100.0),
        ]
    )
    result = dcf_intrinsic_value(hist, _FLAT)
    assert result.intrinsic_value_per_share is None
    assert any("non-positive" in f.lower() for f in result.flags)


def test_missing_shares_is_not_valued() -> None:
    hist = _history([_year(2024, free_cash_flow=12.0)])
    result = dcf_intrinsic_value(hist, _FLAT)
    assert result.intrinsic_value_per_share is None
    assert any("shares" in f.lower() for f in result.flags)


def test_no_cash_flow_or_net_income_is_not_valued() -> None:
    hist = _history([_year(2024, shares_diluted=100.0)])
    result = dcf_intrinsic_value(hist, _FLAT)
    assert result.intrinsic_value_per_share is None
    assert result.fcf_base is None
    assert any("no free cash flow" in f.lower() for f in result.flags)


def test_unavailable_growth_falls_back_to_terminal_growth_flagged() -> None:
    # Single year -> no CAGR computable from any series.
    hist = _history([_year(2024, free_cash_flow=12.0, shares_diluted=100.0)])
    result = dcf_intrinsic_value(hist, DcfAssumptions(terminal_growth=0.03))
    assert result.growth_rate_used == pytest.approx(0.03)
    assert any("growth" in f.lower() for f in result.flags)


def test_estimate_growth_prefers_fcf_then_net_income_then_revenue() -> None:
    fcf = _history(
        [
            _year(2023, free_cash_flow=100.0, net_income=1.0, revenue=1.0),
            _year(2024, free_cash_flow=110.0, net_income=1.0, revenue=1.0),
        ]
    )
    assert estimate_growth(fcf) == pytest.approx(0.10)
    ni = _history(
        [
            _year(2023, net_income=100.0, revenue=1.0),
            _year(2024, net_income=121.0, revenue=1.0),
        ]
    )
    assert estimate_growth(ni) == pytest.approx(0.21)
    rev = _history([_year(2023, revenue=100.0), _year(2024, revenue=105.0)])
    assert estimate_growth(rev) == pytest.approx(0.05)


def test_estimate_growth_none_for_single_year() -> None:
    assert estimate_growth(_history([_year(2024, revenue=100.0)])) is None


def test_discount_rate_must_exceed_terminal_growth() -> None:
    with pytest.raises(ValidationError):
        DcfAssumptions(discount_rate=0.02, terminal_growth=0.03)


@given(
    base=st.floats(min_value=1.0, max_value=1e6),
    scale=st.floats(min_value=1.01, max_value=10.0),
)
def test_intrinsic_value_increases_with_base_cash_flow(base: float, scale: float) -> None:
    def iv(fcf: float) -> float:
        hist = _history([_year(2024, free_cash_flow=fcf, shares_diluted=100.0)])
        value = dcf_intrinsic_value(hist, _FLAT).intrinsic_value_per_share
        assert value is not None
        return value

    low, high = iv(base), iv(base * scale)
    assert high > low
    assert math.isfinite(low) and low > 0
