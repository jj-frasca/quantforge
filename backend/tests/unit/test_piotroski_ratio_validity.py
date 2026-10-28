"""ADR-390: nonfinite derived ratios must refuse before boolean erasure."""

import math
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_fundamentals_quality import _history
from tests.unit.test_piotroski_operand_validity import CONSUMERS, Consumer

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.quality import piotroski_f_score

RATIOS = (
    ("roa_t", 1, "net_income", "total_assets"),
    ("roa_p", 0, "net_income", "total_assets"),
    ("cfo_over_assets_t", 1, "operating_cash_flow", "total_assets"),
    ("lev_t", 1, "long_term_debt", "total_assets"),
    ("lev_p", 0, "long_term_debt", "total_assets"),
    ("cr_t", 1, "total_current_assets", "total_current_liabilities"),
    ("cr_p", 0, "total_current_assets", "total_current_liabilities"),
    ("gm_t", 1, "gross_profit", "revenue"),
    ("gm_p", 0, "gross_profit", "revenue"),
    ("at_t", 1, "revenue", "total_assets"),
    ("at_p", 0, "revenue", "total_assets"),
)


def _overflow_history(
    index: int, numerator: str, denominator: str, sign: float = 1.0
) -> FundamentalsHistory:
    rows = [
        AnnualFundamentals(fiscal_year=2024 + i, revenue=1.0, total_assets=1.0) for i in range(2)
    ]
    rows[index] = rows[index].model_copy(update={numerator: sign * 1e308, denominator: 1e-308})
    return _history(*rows)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_piotroski_nonfinite_derived_ratio_refuses_before_boolean_erasure(
    consumer: Consumer, name: str, index: int, numerator: str, denominator: str, sign: float
) -> None:
    with pytest.raises(ValueError, match=rf"{name} must be finite for Piotroski F-score"):
        consumer(_overflow_history(index, numerator, denominator, sign))


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_piotroski_overflow_exact_accrual_order_refuses(consumer: Consumer) -> None:
    history = _history(
        AnnualFundamentals(fiscal_year=2024, revenue=1.0, total_assets=1.0, net_income=0.0),
        AnnualFundamentals(
            fiscal_year=2025,
            revenue=1.0,
            total_assets=1e-308,
            net_income=1e308,
            operating_cash_flow=1.5e308,
        ),
    )
    assert Fraction(1.5e308) / Fraction(1e-308) > Fraction(1e308) / Fraction(1e-308)
    assert 1.5e308 / 1e-308 == 1e308 / 1e-308 == math.inf
    with pytest.raises(ValueError, match="roa_t must be finite"):
        consumer(history)


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_piotroski_latest_overflow_refuses_without_adjacent_comparison(consumer: Consumer) -> None:
    history = _overflow_history(1, "long_term_debt", "total_assets")
    prior = history.years[0].model_copy(update={"fiscal_year": 2022})
    with pytest.raises(ValueError, match="lev_t must be finite"):
        consumer(_history(prior, history.years[1]))


def test_piotroski_raw_operand_error_precedes_derived_error() -> None:
    history = _overflow_history(1, "net_income", "total_assets")
    latest = history.years[1].model_copy(update={"operating_cash_flow": math.inf})
    with pytest.raises(ValueError, match=r"latest\.operating_cash_flow must be finite"):
        piotroski_f_score(_history(history.years[0], latest))


@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("zero", [0.0, -0.0])
def test_piotroski_zero_denominator_remains_unavailable(
    name: str, index: int, numerator: str, denominator: str, zero: float
) -> None:
    history = _overflow_history(index, numerator, denominator)
    rows = list(history.years)
    rows[index] = rows[index].model_copy(update={denominator: zero})
    assert 0 <= piotroski_f_score(_history(*rows)).score <= 9


@pytest.mark.parametrize("name,index,numerator,denominator", [r for r in RATIOS if r[1] == 0])
def test_piotroski_gap_does_not_compute_prior_overflow(
    name: str, index: int, numerator: str, denominator: str
) -> None:
    history = _overflow_history(index, numerator, denominator)
    prior = history.years[0].model_copy(update={"fiscal_year": 2022})
    f = piotroski_f_score(_history(prior, history.years[1]))
    assert not any(
        (
            f.delta_roa_positive,
            f.delta_leverage_negative,
            f.delta_current_ratio_positive,
            f.delta_gross_margin_positive,
            f.delta_asset_turnover_positive,
        )
    )


@pytest.mark.parametrize(
    "assets,income,cash,score",
    [(1e308, 1e-308, 2e-308, None), (3.0, 7.0, math.nextafter(7.0, math.inf), 3)],
)
def test_piotroski_finite_projection_limits_remain_explicit(
    assets: float, income: float, cash: float, score: int | None
) -> None:
    history = _history(
        AnnualFundamentals(fiscal_year=2024, revenue=1.0, total_assets=1.0, net_income=0.0),
        AnnualFundamentals(
            fiscal_year=2025,
            revenue=1.0,
            total_assets=assets,
            net_income=income,
            operating_cash_flow=cash,
        ),
    )
    assert Fraction(cash) / Fraction(assets) > Fraction(income) / Fraction(assets) > 0
    assert cash / assets == income / assets
    if score is None:
        with pytest.raises(ValueError, match="roa_t must not underflow to zero"):
            piotroski_f_score(history)
        return
    f = piotroski_f_score(history)
    assert not f.accruals_quality
    assert f.score == score


@given(
    income=st.floats(min_value=-1e6, max_value=1e6),
    cash=st.floats(min_value=-1e6, max_value=1e6),
    assets=st.floats(min_value=1.0, max_value=1e6),
)
def test_piotroski_finite_native_comparisons_remain_unchanged(
    income: float, cash: float, assets: float
) -> None:
    history = _history(
        AnnualFundamentals(fiscal_year=2024, revenue=0.0, total_assets=1.0, net_income=0.0),
        AnnualFundamentals(
            fiscal_year=2025,
            revenue=0.0,
            total_assets=assets,
            net_income=income,
            operating_cash_flow=cash,
        ),
    )
    if (income != 0 and income / assets == 0) or (cash != 0 and cash / assets == 0):
        with pytest.raises(ValueError, match="must not underflow to zero"):
            piotroski_f_score(history)
        return
    f = piotroski_f_score(history)
    assert f.roa_positive is (income / assets > 0)
    assert f.delta_roa_positive is (income / assets > 0)
    assert f.accruals_quality is (cash / assets > income / assets)
    assert f.cfo_positive is (cash > 0)
    assert f.score == sum(v for k, v in f.model_dump().items() if k != "score")
