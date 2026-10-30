"""ADR-408: selected DCF base cannot disappear behind an early return."""

import math
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.score import score_valuation


def _history(
    field: str, base: float | None, shares: float | None, count: int = 1
) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="TEST",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=tuple(
            AnnualFundamentals(
                fiscal_year=2025 - count + i,
                revenue=0.0,
                shares_diluted=shares,
                **{field: base},
            )
            for i in range(count)
        ),
    )


def _valuation(history: FundamentalsHistory) -> object:
    return score_valuation(history, 10.0)


@pytest.mark.parametrize("consume", [dcf_intrinsic_value, _valuation])
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("shares", [None, -1.0, 0.0, 10.0])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("field", ["free_cash_flow", "net_income"])
def test_dcf_selected_nonfinite_base_refuses_before_later_paths(
    consume: Callable[[FundamentalsHistory], object],
    count: int,
    shares: float | None,
    invalid: float,
    field: str,
) -> None:
    with pytest.raises(
        ValueError, match=rf"^{field} for fiscal year 2024 must be finite for DCF base$"
    ):
        consume(_history(field, invalid, shares, count))


@pytest.mark.parametrize("shares", [None, 0.0, 10.0])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("field", ["free_cash_flow", "net_income"])
def test_dcf_single_year_record_preserves_base_refusal(
    shares: float | None,
    invalid: float,
    field: str,
) -> None:
    with pytest.raises(
        ValueError, match=rf"^{field} for fiscal year 2024 must be finite for DCF base$"
    ):
        compute_fundamental_record(_history(field, invalid, shares), 10.0)


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("field", ["free_cash_flow", "net_income"])
def test_dcf_base_refusal_precedes_invalid_shares_and_chronology(
    field: str, invalid: float
) -> None:
    history = _history(field, invalid, math.inf)
    row = history.years[0]
    history = history.model_copy(update={"years": (row, row)})
    with pytest.raises(
        ValueError, match=rf"^{field} for fiscal year 2024 must be finite for DCF base$"
    ):
        dcf_intrinsic_value(history)


@pytest.mark.parametrize("field", ["free_cash_flow", "net_income"])
@pytest.mark.parametrize("base", [None, -12.0, -0.0, 0.0])
def test_dcf_finite_nonpositive_or_missing_base_keeps_early_return(
    field: str, base: float | None
) -> None:
    result = dcf_intrinsic_value(_history(field, base, math.inf))
    assert result.intrinsic_value_per_share is None
    assert result.fcf_base == base
    assert result.flags[-1] == (
        "no free cash flow or net income to value"
        if base is None
        else "non-positive base cash flow — DCF not meaningful"
    )


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_dcf_valid_selected_fcf_does_not_inspect_invalid_proxy(invalid: float) -> None:
    history = _history("free_cash_flow", 12.0, 10.0)
    row = history.years[0].model_copy(update={"net_income": invalid})
    result = dcf_intrinsic_value(history.model_copy(update={"years": (row,)}))
    assert result.fcf_base == 12.0
    assert not result.fcf_is_net_income_proxy
    assert result.intrinsic_value_per_share is not None
    assert math.isfinite(result.intrinsic_value_per_share)


@given(base=st.floats(min_value=1.0, max_value=1e6), proxy=st.booleans())
def test_dcf_finite_selected_base_preserves_perpetuity(base: float, proxy: bool) -> None:
    field = "net_income" if proxy else "free_cash_flow"
    assumptions = DcfAssumptions(terminal_growth=0.0, min_growth=0.0, max_growth=0.0)
    result = dcf_intrinsic_value(_history(field, base, 10.0), assumptions)
    assert result.intrinsic_value_per_share == pytest.approx(base / 0.10 / 10.0)
    assert result.fcf_base == base
    assert result.fcf_is_net_income_proxy is proxy
