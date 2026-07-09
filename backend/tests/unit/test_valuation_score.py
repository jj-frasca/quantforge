"""Composite UndervaluationScore combining own-history multiples + DCF margin of safety (ADR-022).
Cited to the latest 10-K; missing inputs become flags, never silent defaults. Rule-6 honest."""

import pytest

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.valuation import UndervaluationScore, score_valuation
from app.research.valuation.intrinsic_value import DcfAssumptions

# Flat-growth DCF -> perpetuity FCF/r: base FCF 600, r=0.10, 100 shares -> intrinsic 60/share.
_FLAT = DcfAssumptions(
    discount_rate=0.10, terminal_growth=0.0, projection_years=2, max_growth=0.0, min_growth=0.0
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


def _rich() -> FundamentalsHistory:
    return _history(
        [
            AnnualFundamentals(
                fiscal_year=2022,
                revenue=1000.0,
                eps=4.0,
                price=40.0,
                shares_diluted=100.0,
                free_cash_flow=500.0,
            ),
            AnnualFundamentals(
                fiscal_year=2023,
                revenue=1100.0,
                eps=5.0,
                price=50.0,
                shares_diluted=100.0,
                free_cash_flow=550.0,
            ),
            AnnualFundamentals(
                fiscal_year=2024,
                revenue=1200.0,
                eps=5.0,
                price=60.0,
                shares_diluted=100.0,
                free_cash_flow=600.0,
            ),
        ]
    )


def test_composite_blends_multiples_and_margin_of_safety() -> None:
    result = score_valuation(_rich(), price=55.0, assumptions=_FLAT)
    assert isinstance(result, UndervaluationScore)
    # P/E 11 and P/S 4.583 both rank at 2/3 -> each contributes (1 - 2/3) = 1/3.
    assert result.pe_percentile == pytest.approx(2 / 3)
    assert result.ps_percentile == pytest.approx(2 / 3)
    # intrinsic 60 vs price 55 -> margin of safety (60-55)/60 = 0.08333.
    assert result.intrinsic_value_per_share == pytest.approx(60.0)
    assert result.margin_of_safety == pytest.approx(5 / 60)
    # mean of [1/3, 1/3, 0.08333] = 0.25.
    assert result.score == pytest.approx(0.25)
    assert result.flags == []


def test_carries_citation_and_price() -> None:
    result = score_valuation(_rich(), price=55.0, assumptions=_FLAT)
    assert result.symbol == "AAPL"
    assert result.cik == 320193
    assert result.entity_name == "Apple Inc."
    assert result.fiscal_year == 2024
    assert result.form == "10-K"
    assert result.accession_number == "a-2024"
    assert result.source == "SEC EDGAR"
    assert result.current_price == 55.0
    assert result.growth_rate_used == 0.0
    assert result.fcf_is_net_income_proxy is False


def test_margin_of_safety_is_negative_when_overvalued_and_score_clamps() -> None:
    # intrinsic 60, price 100 -> negative margin of safety; the score component clamps at 0.
    result = score_valuation(_rich(), price=100.0, assumptions=_FLAT)
    assert result.margin_of_safety == pytest.approx((60.0 - 100.0) / 60.0)
    assert result.margin_of_safety < 0
    # P/E 100/5=20 and P/S 100*100/1200=8.33 are the most expensive ever -> percentile 1.0.
    assert result.pe_percentile == pytest.approx(1.0)
    assert result.ps_percentile == pytest.approx(1.0)
    # components [0, 0, clamp(-0.66)=0] -> score 0.
    assert result.score == pytest.approx(0.0)


def test_no_components_yields_none_score_and_flag() -> None:
    bare = _history([AnnualFundamentals(fiscal_year=2024, revenue=1000.0)])
    result = score_valuation(bare, price=55.0)
    assert result.pe_ratio is None
    assert result.ps_ratio is None
    assert result.intrinsic_value_per_share is None
    assert result.margin_of_safety is None
    assert result.score is None
    assert any("no valuation components" in f.lower() for f in result.flags)


def test_default_assumptions_are_used_when_omitted() -> None:
    result = score_valuation(_rich(), price=55.0)
    assert result.intrinsic_value_per_share is not None  # DCF ran with defaults
    assert result.score is not None


def test_round_trips_json() -> None:
    result = score_valuation(_rich(), price=55.0, assumptions=_FLAT)
    assert UndervaluationScore.model_validate_json(result.model_dump_json()) == result
