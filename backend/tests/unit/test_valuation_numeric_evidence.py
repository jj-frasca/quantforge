"""ADR-373: final valuation evidence refuses undefined numeric claims."""

import json
import math
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation import UndervaluationScore, score_valuation

NUMERIC_FIELDS = [
    "current_price",
    "pe_ratio",
    "pe_percentile",
    "ps_ratio",
    "ps_percentile",
    "intrinsic_value_per_share",
    "margin_of_safety",
    "growth_rate_used",
    "score",
]


def _payload() -> dict[str, object]:
    return {
        "symbol": "SYNTH",
        "cik": 1,
        "entity_name": "Synthetic",
        "fiscal_year": 2025,
        "form": "10-K",
        "accession_number": "synthetic",
        "source_url": "synthetic",
        "current_price": 10.0,
        "pe_ratio": 10.0,
        "pe_percentile": 0.2,
        "ps_ratio": 2.0,
        "ps_percentile": 0.2,
        "intrinsic_value_per_share": 50.0,
        "margin_of_safety": 0.8,
        "growth_rate_used": 0.03,
        "fcf_is_net_income_proxy": False,
        "score": 0.8,
        "flags": ["synthetic"],
    }


def _history(magnitude: float = 1e308) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="SYNTH",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="synthetic",
        years=tuple(
            AnnualFundamentals(
                fiscal_year=year,
                period_end=date(year, 12, 31),
                revenue=magnitude,
                net_income=magnitude,
                free_cash_flow=magnitude,
                eps=1.0,
                shares_diluted=1e6,
                price=10.0,
            )
            for year in (2024, 2025)
        ),
    )


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("via_json", [False, True])
def test_valuation_model_refuses_nonfinite_numeric_evidence(
    field: str, value: float, via_json: bool
) -> None:
    payload = {**_payload(), field: value}
    with pytest.raises(ValidationError, match=field):
        if via_json:
            UndervaluationScore.model_validate_json(json.dumps(payload))
        else:
            UndervaluationScore.model_validate(payload)


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@settings(max_examples=30, deadline=None)
@given(value=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_valuation_field_retains_exact_value_through_json(field: str, value: float) -> None:
    model = UndervaluationScore.model_validate({**_payload(), field: value})
    restored = UndervaluationScore.model_validate_json(model.model_dump_json())
    assert getattr(model, field).hex() == value.hex()
    assert getattr(restored, field).hex() == value.hex()
    assert restored.flags == ["synthetic"]


@pytest.mark.parametrize("field", NUMERIC_FIELDS[1:])
def test_nullable_valuation_evidence_stays_missing(field: str) -> None:
    model = UndervaluationScore.model_validate({**_payload(), field: None})
    restored = UndervaluationScore.model_validate_json(model.model_dump_json())
    assert getattr(restored, field) is None


def test_finite_canonical_extreme_input_refuses_unmeasurable_producer_output() -> None:
    history = _history()
    assert all(math.isfinite(year.free_cash_flow) for year in history.years)
    with pytest.raises(ValidationError, match="finite"):
        score_valuation(history, 10.0)


def test_value_provider_propagates_unmeasurable_score_instead_of_missingness() -> None:
    provider = make_value_provider(
        lambda symbol: _history(),
        lambda symbol: [(date(2024, 12, 31), 10.0), (date(2025, 12, 31), 10.0)],
    )
    with pytest.raises(ValidationError, match="finite"):
        provider("SYNTH")


@pytest.mark.parametrize("screen_enabled", [False, True])
def test_record_first_hunt_records_score_refusal_before_downstream_acquisition(
    screen_enabled: bool,
) -> None:
    events: list[str] = []

    def history_provider(symbol: str) -> FundamentalsHistory:
        events.append("history")
        return _history()

    def provider_prices(symbol: str) -> list[tuple[date, float]]:
        events.append("provider-prices")
        return [(date(2024, 12, 31), 10.0), (date(2025, 12, 31), 10.0)]

    def downstream_frame(symbol: str) -> None:
        events.append("downstream-frame")
        raise ValueError("DOWNSTREAM_SENTINEL_NO_SEARCH")

    result = run_universe_hunt(
        ["SYNTH"],
        ["sma"],
        downstream_frame,
        value_provider=make_value_provider(history_provider, provider_prices),
        value_config=ValueGateConfig() if screen_enabled else None,
    )
    assert "finite" in result.errors["SYNTH"]
    assert result.filtered == {}
    assert result.experiments == []
    assert events == ["history", "provider-prices"]
