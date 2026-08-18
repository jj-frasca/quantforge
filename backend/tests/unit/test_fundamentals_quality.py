"""ADR-029 Layer 2: cited fundamental quality scorers over FundamentalsHistory.

Each scorer is pure and conservative — a missing input never awards a Piotroski point, and every
composite flags what it could not compute (CLAUDE.md rule 6). The fixtures build two-year histories
because the F-Score's trend signals (ΔROA, Δleverage, ...) need a prior year."""

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.quality import (
    financial_safety,
    gross_profitability,
    piotroski_f_score,
    quality_score,
)


def _year(fy: int, **overrides: float | None) -> AnnualFundamentals:
    base: dict[str, float | None] = {
        "fiscal_year": fy,
        "revenue": 1000.0,
        "net_income": 100.0,
        "shares_diluted": 50.0,
        "total_assets": 2000.0,
        "total_current_assets": 800.0,
        "total_current_liabilities": 400.0,
        "long_term_debt": 500.0,
        "gross_profit": 400.0,
        "operating_cash_flow": 150.0,
        "retained_earnings": 300.0,
        "total_equity": 1200.0,
    }
    base.update(overrides)
    return AnnualFundamentals(**base)  # type: ignore[arg-type]


def _history(*years: AnnualFundamentals) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="TEST",
        cik=320193,
        entity_name="Test Corp",
        form="10-K",
        accession_number="0000000000-00-000000",
        source_url="https://www.sec.gov/cgi-bin/browse-edgar",
        years=tuple(years),
    )


# ---- Piotroski F-Score ---------------------------------------------------------------------------


def test_perfect_year_over_year_improvement_scores_nine() -> None:
    prior = _year(
        2023,
        net_income=50.0,  # ROA 2.5% -> improves to 5%
        total_assets=2000.0,
        long_term_debt=600.0,  # leverage 30% -> falls to 25%
        total_current_assets=600.0,  # current ratio 1.5 -> rises to 2.0
        total_current_liabilities=400.0,
        gross_profit=300.0,  # margin 30% -> rises to 40%
        operating_cash_flow=120.0,
        shares_diluted=50.0,  # unchanged -> no dilution passes
    )
    latest = _year(
        2024
    )  # revenue 1000/assets 2000 -> asset turnover 0.5 vs prior 0.5... make it rise
    latest = latest.model_copy(update={"revenue": 1100.0, "gross_profit": 440.0})
    f = piotroski_f_score(_history(prior, latest))
    assert f.score == 9
    assert all(
        [
            f.roa_positive,
            f.cfo_positive,
            f.delta_roa_positive,
            f.accruals_quality,
            f.delta_leverage_negative,
            f.delta_current_ratio_positive,
            f.no_dilution,
            f.delta_gross_margin_positive,
            f.delta_asset_turnover_positive,
        ]
    )


def test_deteriorating_company_scores_low() -> None:
    prior = _year(2023, net_income=200.0, long_term_debt=200.0, gross_profit=500.0)
    latest = _year(
        2024,
        net_income=-50.0,  # ROA negative + falling
        operating_cash_flow=-30.0,  # cfo negative
        long_term_debt=800.0,  # leverage rising
        gross_profit=100.0,  # margin falling
        shares_diluted=80.0,  # dilution
    )
    f = piotroski_f_score(_history(prior, latest))
    assert f.score <= 2
    assert not f.roa_positive
    assert not f.cfo_positive
    assert not f.no_dilution


def test_single_year_history_scores_zero() -> None:
    f = piotroski_f_score(_history(_year(2024)))
    assert f.score == 0
    assert not f.delta_roa_positive  # no prior year to compare


def test_missing_inputs_never_award_a_point() -> None:
    prior = _year(2023)
    latest = _year(
        2024,
        net_income=None,
        operating_cash_flow=None,
        total_assets=None,
        long_term_debt=None,
        total_current_assets=None,
        gross_profit=None,
        shares_diluted=None,
    )
    f = piotroski_f_score(_history(prior, latest))
    assert f.score == 0


def test_no_dilution_passes_when_shares_flat() -> None:
    prior = _year(2023, shares_diluted=50.0)
    latest = _year(2024, shares_diluted=50.0)
    assert piotroski_f_score(_history(prior, latest)).no_dilution


# ---- Gross profitability (Novy-Marx) -------------------------------------------------------------


def test_gross_profitability_is_latest_gp_over_assets() -> None:
    assert gross_profitability(_history(_year(2023), _year(2024))) == 400.0 / 2000.0


def test_gross_profitability_none_when_missing() -> None:
    assert gross_profitability(_history(_year(2024, gross_profit=None))) is None
    assert gross_profitability(_history(_year(2024, total_assets=0.0))) is None


def test_gross_profitability_none_on_empty_history() -> None:
    assert gross_profitability(_history()) is None


# ---- Financial safety ----------------------------------------------------------------------------


def test_financial_safety_computes_leverage_and_liquidity() -> None:
    s = financial_safety(_history(_year(2024)))
    assert s.leverage_ratio == (2000.0 - 1200.0) / 2000.0  # total liabilities / assets
    assert s.current_ratio == 800.0 / 400.0
    assert s.negative_retained_earnings is False


def test_financial_safety_flags_accumulated_deficit() -> None:
    s = financial_safety(_history(_year(2024, retained_earnings=-100.0)))
    assert s.negative_retained_earnings is True


def test_financial_safety_none_fields_when_missing() -> None:
    s = financial_safety(_history(_year(2024, total_equity=None, retained_earnings=None)))
    assert s.leverage_ratio is None
    assert s.negative_retained_earnings is None


def test_financial_safety_empty_history() -> None:
    s = financial_safety(_history())
    assert s.leverage_ratio is None and s.current_ratio is None


# ---- Composite quality_score ---------------------------------------------------------------------


def test_quality_score_blends_available_legs_into_unit_interval() -> None:
    q = quality_score(_history(_year(2023), _year(2024)))
    assert q.score is not None and 0.0 <= q.score <= 1.0
    assert q.f_score.score >= 1
    assert q.gross_profitability == 400.0 / 2000.0
    assert q.flags == []


def test_quality_score_drops_missing_legs_and_flags_them() -> None:
    # gross_profit + safety inputs gone -> those legs drop, F-Score leg carries the score.
    latest = _year(
        2024,
        gross_profit=None,
        total_equity=None,
        retained_earnings=None,
        total_current_assets=None,
        total_current_liabilities=None,
    )
    q = quality_score(_history(_year(2023), latest))
    assert q.score is not None
    assert "gross profitability unavailable" in q.flags
    assert "financial safety unavailable" in q.flags


def test_quality_score_none_on_empty_history() -> None:
    q = quality_score(_history())
    assert q.score is None
    assert "no fundamentals history" in q.flags


def test_quality_score_strong_company_beats_weak() -> None:
    strong = quality_score(_history(_year(2023, net_income=50.0), _year(2024)))
    weak_latest = _year(
        2024,
        net_income=-100.0,
        operating_cash_flow=-50.0,
        gross_profit=10.0,
        long_term_debt=1900.0,
        total_equity=50.0,  # near-insolvent -> leverage ~97.5%
        retained_earnings=-500.0,
    )
    weak = quality_score(_history(_year(2023), weak_latest))
    assert strong.score is not None and weak.score is not None
    assert strong.score > weak.score
