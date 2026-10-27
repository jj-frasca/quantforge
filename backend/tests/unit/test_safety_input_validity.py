"""ADR-385: present nonfinite safety operands cannot disappear into shortcuts."""

from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.distress import financial_distress, make_distress_provider
from app.research.fundamentals.quality import financial_safety, quality_score
from app.research.fundamentals.record import compute_fundamental_record

_FIELDS = (
    "total_assets",
    "total_equity",
    "total_current_assets",
    "total_current_liabilities",
    "retained_earnings",
)


def _history(**fields: float | None) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="SYN",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="synthetic",
        years=(AnnualFundamentals(fiscal_year=2025, revenue=100, **fields),),
    )


def _provider(history: FundamentalsHistory) -> object:
    return make_distress_provider(lambda symbol: history)("SYN")


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize(
    "consume",
    [financial_safety, quality_score, compute_fundamental_record, financial_distress, _provider],
)
def test_safety_present_nonfinite_operands_refuse_before_erasure(
    field: str, value: float, consume: Callable[[FundamentalsHistory], object]
) -> None:
    with pytest.raises(ValueError, match=field) as error:
        consume(_history(**{field: value}))
    assert not isinstance(error.value, ValidationError)  # Input preflight precedes output models.


@pytest.mark.parametrize(
    "fields,invalid",
    [
        (
            {"total_current_assets": float("nan"), "total_current_liabilities": 0.0},
            "total_current_assets",
        ),
        ({"total_assets": 0.0, "total_equity": float("nan")}, "total_equity"),
        ({"total_assets": float("inf"), "total_equity": None}, "total_assets"),
        (
            {"total_current_assets": 100.0, "total_current_liabilities": float("inf")},
            "total_current_liabilities",
        ),
    ],
)
def test_safety_missing_peer_zero_denominator_and_finite_projection_do_not_hide_invalidity(
    fields: dict[str, float | None], invalid: str
) -> None:
    with pytest.raises(ValueError, match=invalid):
        financial_safety(_history(**fields))


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("value", [None, -100.0, -0.0, 100.0])
def test_safety_finite_nullable_and_signed_operands_remain(field: str, value: float | None) -> None:
    financial_safety(_history(**{field: value}))


def test_safety_preflight_reports_first_named_invalid_field() -> None:
    with pytest.raises(ValueError, match="total_assets"):
        financial_safety(_history(total_assets=float("nan"), retained_earnings=float("inf")))


def test_safety_invalid_retained_earnings_preserves_explicit_provider_failure() -> None:
    calls: list[str] = []
    history = _history(
        net_income=-1.0,
        operating_cash_flow=-2.0,
        total_assets=100.0,
        total_equity=-100.0,
        retained_earnings=float("nan"),
    )

    def provide_history(symbol: str) -> FundamentalsHistory:
        calls.append(symbol)
        return history

    with pytest.raises(ValueError, match="retained_earnings"):
        make_distress_provider(provide_history)("SYN")
    assert calls == ["SYN"]


@pytest.mark.parametrize(
    "fields,component",
    [
        ({"total_assets": 1e308, "total_equity": -1e308}, "leverage_ratio"),
        ({"total_current_assets": 1e308, "total_current_liabilities": 1e-308}, "current_ratio"),
    ],
)
def test_safety_finite_input_overflow_keeps_output_validation(
    fields: dict[str, float], component: str
) -> None:
    with pytest.raises(ValidationError, match=component):
        financial_safety(_history(**fields))


def test_safety_empty_and_invalid_older_year_remain_outside_latest_preflight() -> None:
    history = _history(total_assets=100.0, total_equity=50.0)
    older = AnnualFundamentals(fiscal_year=2024, revenue=100, retained_earnings=float("nan"))
    with_older = history.model_copy(update={"years": (older, history.years[0])})
    assert financial_safety(with_older) == financial_safety(history)
    empty = history.model_copy(update={"years": ()})
    assert financial_safety(empty).model_dump() == {
        "leverage_ratio": None,
        "current_ratio": None,
        "negative_retained_earnings": None,
    }


@given(
    st.fixed_dictionaries(
        {field: st.one_of(st.none(), st.integers(-1000, 1000).map(float)) for field in _FIELDS}
    )
)
def test_safety_finite_missing_operands_keep_quality_in_unit_interval(
    fields: dict[str, float | None],
) -> None:
    result = quality_score(_history(**fields))
    assert result.score is not None and 0.0 <= result.score <= 1.0
