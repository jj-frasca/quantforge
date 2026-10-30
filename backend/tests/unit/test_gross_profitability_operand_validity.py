"""ADR-405: consumed gross-profitability operands must be finite."""

import math
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.quality import (
    gross_profitability,
    piotroski_f_score,
    quality_score,
)
from app.research.fundamentals.record import compute_fundamental_record


def _year(fiscal_year: int = 2025, **overrides: float | None) -> AnnualFundamentals:
    values: dict[str, float | None] = {"gross_profit": 25.0, "total_assets": 100.0}
    values.update(overrides)
    return AnnualFundamentals(fiscal_year=fiscal_year, revenue=100.0, **values)


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


CONSUMERS: tuple[Callable[[FundamentalsHistory], object], ...] = (
    gross_profitability,
    quality_score,
    compute_fundamental_record,
)


@pytest.mark.parametrize("consume", CONSUMERS)
@pytest.mark.parametrize("field", ["gross_profit", "total_assets"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("peer", [None, 0.0, -1.0, 100.0])
def test_gp_refuses_present_nonfinite_operands_before_shortcuts(
    consume: Callable[[FundamentalsHistory], object],
    field: str,
    invalid: float,
    peer: float | None,
) -> None:
    other = "total_assets" if field == "gross_profit" else "gross_profit"
    with pytest.raises(ValueError, match=rf"^{field} must be finite for gross profitability$"):
        consume(_history(_year(**{field: invalid, other: peer})))


@pytest.mark.parametrize("consume", CONSUMERS)
def test_gp_first_invalid_operand_is_gross_profit(
    consume: Callable[[FundamentalsHistory], object],
) -> None:
    with pytest.raises(ValueError, match=r"^gross_profit must be finite for gross profitability$"):
        consume(_history(_year(gross_profit=math.nan, total_assets=math.inf)))


@pytest.mark.parametrize("consume", [quality_score, compute_fundamental_record])
@pytest.mark.parametrize("equity", [math.nan, -1e308])
def test_single_year_gp_refusal_precedes_safety_errors(
    consume: Callable[[FundamentalsHistory], object],
    equity: float,
) -> None:
    with pytest.raises(ValueError, match=r"^gross_profit must be finite for gross profitability$"):
        consume(_history(_year(gross_profit=math.nan, total_assets=1e308, total_equity=equity)))


@pytest.mark.parametrize("consume", [quality_score, compute_fundamental_record])
def test_two_year_piotroski_refusal_still_precedes_gp(
    consume: Callable[[FundamentalsHistory], object],
) -> None:
    with pytest.raises(
        ValueError, match=r"^latest.net_income must be finite for Piotroski F-score$"
    ):
        consume(_history(_year(2024), _year(net_income=math.nan, gross_profit=math.nan)))


@pytest.mark.parametrize("consume", CONSUMERS)
@pytest.mark.parametrize("field", ["gross_profit", "total_assets"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_gp_ignores_invalid_older_operands(
    consume: Callable[[FundamentalsHistory], object],
    field: str,
    invalid: float,
) -> None:
    latest = _year()
    # A gap also disables prior-year Piotroski trend inputs for composite consumers.
    assert consume(_history(_year(2020, **{field: invalid}), latest)) == consume(
        _history(_year(2020), latest)
    )


def test_gp_empty_history_and_single_year_piotroski_policy_stay() -> None:
    assert gross_profitability(_history()) is None
    assert quality_score(_history()).score is None
    assert compute_fundamental_record(_history()).quality_score is None
    assert piotroski_f_score(_history(_year(gross_profit=math.nan))).score == 0


def test_gp_finite_derived_overflow_is_separate_from_raw_input_validity() -> None:
    source = _history(_year(gross_profit=1e308, total_assets=1e-308))
    assert gross_profitability(source) == math.inf
    assert quality_score(source).gross_profitability == math.inf
    with pytest.raises(ValidationError, match="gross_profitability"):
        compute_fundamental_record(source)


def test_gp_finite_underflow_and_unrelated_safety_error_stay() -> None:
    source = _history(_year(gross_profit=-1e-308, total_assets=1e308))
    result = gross_profitability(source)
    assert result is not None and result.hex() == (-0.0).hex()
    assert compute_fundamental_record(source).gross_profitability == -0.0
    invalid_safety = _history(_year(total_equity=math.nan))
    assert gross_profitability(invalid_safety) == 0.25
    with pytest.raises(ValueError, match=r"^total_equity must be finite for financial safety$"):
        quality_score(invalid_safety)


@given(
    gp=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
    assets=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
)
def test_gp_finite_or_missing_operands_preserve_native_division(
    gp: float | None,
    assets: float | None,
) -> None:
    result = gross_profitability(_history(_year(gross_profit=gp, total_assets=assets)))
    if gp is None or assets is None or assets == 0:
        assert result is None
    else:
        assert result is not None
        assert result.hex() == (gp / assets).hex()
