"""ADR-404: nonfinite profit/cash evidence must not become distress booleans."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.distress import (
    DistressScreen,
    financial_distress,
    make_distress_provider,
)


def _year(**overrides: float | None) -> AnnualFundamentals:
    values: dict[str, float | None] = {
        "net_income": -1.0,
        "operating_cash_flow": -1.0,
        "total_assets": 100.0,
        "total_equity": -10.0,
    }
    values.update(overrides)
    return AnnualFundamentals(fiscal_year=2025, revenue=100.0, **values)


def _history(*years: AnnualFundamentals) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="TEST",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=years,
    )


def _consume(history: FundamentalsHistory, wrapped: bool) -> DistressScreen | None:
    if wrapped:
        return make_distress_provider(lambda symbol: history)("TEST")
    return financial_distress(history)


@pytest.mark.parametrize("field", ["net_income", "operating_cash_flow"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("peer", [None, 0.0, -1.0])
@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_refuses_present_nonfinite_profit_operand(
    field: str, invalid: float, peer: float | None, wrapped: bool
) -> None:
    other = "operating_cash_flow" if field == "net_income" else "net_income"
    source = _history(_year(**{field: invalid, other: peer}))
    with pytest.raises(ValueError, match=rf"^{field} must be finite for financial distress$"):
        _consume(source, wrapped)


@pytest.mark.parametrize("field", ["net_income", "operating_cash_flow"])
@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("prior_year", [2024, 2020])
def test_distress_refuses_invalid_latest_profit_with_any_prior(
    field: str, wrapped: bool, prior_year: int
) -> None:
    prior = AnnualFundamentals(fiscal_year=prior_year, revenue=100.0)
    with pytest.raises(ValueError, match=rf"^{field} must be finite for financial distress$"):
        _consume(_history(prior, _year(**{field: math.nan})), wrapped)


@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_income_refusal_precedes_cash_flow_refusal(wrapped: bool) -> None:
    with pytest.raises(ValueError, match=r"^net_income must be finite for financial distress$"):
        _consume(_history(_year(net_income=math.nan, operating_cash_flow=math.inf)), wrapped)


@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_refuses_profit_even_with_healthy_or_absent_balance_sheet(wrapped: bool) -> None:
    for balance in ({"total_equity": 50.0}, {"total_assets": None, "total_equity": None}):
        with pytest.raises(ValueError, match=r"^net_income must be finite for financial distress$"):
            _consume(_history(_year(net_income=math.nan, **balance)), wrapped)


@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_preserves_safety_source_error_precedence(wrapped: bool) -> None:
    with pytest.raises(ValueError, match=r"^total_assets must be finite for financial safety$"):
        _consume(_history(_year(total_assets=math.nan, net_income=math.nan)), wrapped)


@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_preserves_safety_arithmetic_error_precedence(wrapped: bool) -> None:
    with pytest.raises(ValidationError, match="leverage_ratio"):
        _consume(
            _history(_year(total_assets=1e308, total_equity=-1e308, net_income=math.nan)), wrapped
        )


@pytest.mark.parametrize("field", ["net_income", "operating_cash_flow"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_distress_ignores_nonfinite_profit_in_old_rows(field: str, invalid: float) -> None:
    old = AnnualFundamentals(fiscal_year=2020, revenue=100.0, **{field: invalid})
    assert financial_distress(_history(old, _year())) == financial_distress(_history(_year()))


@pytest.mark.parametrize("wrapped", [False, True])
def test_distress_empty_history_remains_not_distressed(wrapped: bool) -> None:
    screen = _consume(_history(), wrapped)
    assert screen is not None
    assert screen.model_dump(mode="json") == {"distressed": False, "reasons": []}


@pytest.mark.parametrize("error", [ValueError, KeyError, OSError])
def test_distress_provider_preserves_acquisition_missingness(error: type[Exception]) -> None:
    def unavailable(symbol: str) -> FundamentalsHistory:
        raise error("synthetic acquisition failure")

    assert make_distress_provider(unavailable)("TEST") is None


@given(
    income=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
    cash_flow=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
    equity=st.integers(min_value=-100, max_value=100),
    current_assets=st.integers(min_value=0, max_value=200),
)
def test_distress_preserves_finite_native_profit_signs(
    income: float | None, cash_flow: float | None, equity: int, current_assets: int
) -> None:
    source = _history(
        _year(
            net_income=income,
            operating_cash_flow=cash_flow,
            total_equity=float(equity),
            total_current_assets=float(current_assets),
            total_current_liabilities=100.0,
        )
    )
    expected = (
        income is not None
        and income < 0
        and cash_flow is not None
        and cash_flow < 0
        and (equity < 0 or current_assets < 100)
    )
    direct = financial_distress(source)
    assert direct.distressed is expected
    assert make_distress_provider(lambda symbol: source)("TEST") == direct
