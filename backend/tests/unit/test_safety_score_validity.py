"""ADR-384: refuse nonfinite safety components before quality/distress use."""

import json
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import (
    AnnualFundamentals,
    FundamentalsHistory,
    parse_company_facts_history,
)
from app.research.fundamentals.distress import financial_distress, make_distress_provider
from app.research.fundamentals.quality import SafetyScore, financial_safety, quality_score
from app.research.fundamentals.record import compute_fundamental_record


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


@pytest.mark.parametrize("field", ["leverage_ratio", "current_ratio"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("route", ["constructor", "dict", "json"])
def test_safety_score_nonfinite_numeric_fields_refuse(field: str, value: float, route: str) -> None:
    values = {"leverage_ratio": None, "current_ratio": None, "negative_retained_earnings": None}
    values[field] = value
    with pytest.raises(ValidationError, match=field):
        if route == "constructor":
            SafetyScore(**values)
        elif route == "dict":
            SafetyScore.model_validate(values)
        else:
            SafetyScore.model_validate_json(json.dumps(values))


@pytest.mark.parametrize("field", ["leverage_ratio", "current_ratio"])
@pytest.mark.parametrize("value", [None, -100.0, -0.0, 0.0, 100.0, "1.25", True])
def test_safety_score_finite_nullable_and_coercible_values_remain(
    field: str, value: object
) -> None:
    values = {"leverage_ratio": None, "current_ratio": None, "negative_retained_earnings": None}
    values[field] = value
    score = SafetyScore.model_validate(values)
    assert getattr(score, field) == (None if value is None else float(value))
    assert SafetyScore.model_validate_json(score.model_dump_json()) == score


@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False),
)
def test_safety_score_finite_components_round_trip(leverage: float, current: float) -> None:
    score = SafetyScore(
        leverage_ratio=leverage, current_ratio=current, negative_retained_earnings=None
    )
    assert score.leverage_ratio == leverage
    assert score.current_ratio == current
    assert SafetyScore.model_validate_json(score.model_dump_json()) == score


@pytest.mark.parametrize(
    "fields",
    [
        {"total_current_assets": float("nan"), "total_current_liabilities": 100.0},
        {"total_assets": 100.0, "total_equity": float("nan")},
        {"total_current_assets": 1e308, "total_current_liabilities": 1e-308},
        {"total_assets": 1e308, "total_equity": -1e308},
    ],
    ids=[
        "nan-liquidity",
        "nan-leverage",
        "finite-liquidity-overflow",
        "finite-liabilities-overflow",
    ],
)
@pytest.mark.parametrize("consume", [financial_safety, quality_score, compute_fundamental_record])
def test_safety_producer_refuses_before_nonfinite_evidence_becomes_finite_quality(
    fields: dict[str, float], consume: Callable[[FundamentalsHistory], object]
) -> None:
    with pytest.raises(ValueError, match="finite"):
        consume(_history(**fields))


@pytest.mark.parametrize("insolvent", [False, True])
def test_distress_provider_does_not_turn_invalid_liquidity_into_missingness(
    insolvent: bool,
) -> None:
    calls: list[str] = []
    history = _history(
        net_income=-1.0,
        operating_cash_flow=-2.0,
        total_assets=100.0,
        total_equity=-100.0 if insolvent else 50.0,
        total_current_assets=float("nan"),
        total_current_liabilities=100.0,
    )

    def provide_history(symbol: str) -> FundamentalsHistory:
        calls.append(symbol)
        return history

    with pytest.raises(ValueError, match="total_current_assets"):
        make_distress_provider(provide_history)("SYN")
    assert calls == ["SYN"]


@pytest.mark.parametrize("error", [ValueError, KeyError, OSError])
def test_distress_provider_history_acquisition_fallback_remains(error: type[Exception]) -> None:
    def provide_history(symbol: str) -> FundamentalsHistory:
        raise error("unavailable")

    assert make_distress_provider(provide_history)("SYN") is None


@pytest.mark.parametrize("current", [None, 0.0, 200.0])
def test_safety_missing_zero_denominator_and_finite_distress_veto_remain(
    current: float | None,
) -> None:
    history = _history(
        net_income=-1.0,
        operating_cash_flow=-2.0,
        total_assets=100.0,
        total_equity=-100.0,
        total_current_assets=current,
        total_current_liabilities=0.0,
    )
    assert financial_safety(history).current_ratio is None
    assert financial_distress(history).distressed is True
    assert "liabilities exceed assets (negative equity)" in financial_distress(history).reasons


def test_synthetic_company_facts_nan_safety_refuses_at_consumption() -> None:
    def fact(value: float) -> dict[str, object]:
        return {
            "units": {
                "USD": [
                    {
                        "fy": 2025,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2026-01-01",
                        "end": "2025-12-31",
                        "accn": "synthetic",
                        "val": value,
                    }
                ]
            }
        }

    history = parse_company_facts_history(
        {
            "cik": 1,
            "facts": {
                "us-gaap": {
                    "Revenues": fact(100.0),
                    "AssetsCurrent": fact(float("nan")),
                    "LiabilitiesCurrent": fact(100.0),
                }
            },
        },
        "SYN",
    )
    with pytest.raises(ValueError, match="total_current_assets"):
        compute_fundamental_record(history)
