"""ADR-382: malformed DCF settings cannot hide behind finite producer outputs."""

import json
from datetime import date

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.lab.value_filter import make_value_provider
from app.research.lab.value_wiring import make_hunt_value_provider
from app.research.valuation.intrinsic_value import (
    DcfAssumptions,
    IntrinsicValueResult,
    dcf_intrinsic_value,
)

_FLOAT_FIELDS = ["discount_rate", "terminal_growth", "min_growth", "max_growth"]
_NONFINITE = [float("nan"), float("inf"), float("-inf")]


@pytest.mark.parametrize("field", _FLOAT_FIELDS)
@pytest.mark.parametrize("value", _NONFINITE, ids=["nan", "positive_inf", "negative_inf"])
@pytest.mark.parametrize("path", ["constructor", "dictionary", "json"])
def test_dcf_assumptions_refuse_nonfinite_float_fields(field: str, value: float, path: str) -> None:
    raw = {field: value}
    with pytest.raises(ValidationError):
        if path == "constructor":
            DcfAssumptions(**raw)
        elif path == "dictionary":
            DcfAssumptions.model_validate(raw)
        else:
            DcfAssumptions.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize("field", ["min_growth", "max_growth"])
@pytest.mark.parametrize("value", _NONFINITE, ids=["nan", "positive_inf", "negative_inf"])
@pytest.mark.parametrize("path", ["dictionary", "json"])
def test_raw_nested_result_refuses_nonfinite_growth_settings(
    field: str, value: float, path: str
) -> None:
    raw = {
        "intrinsic_value_per_share": 120.0,
        "growth_rate_used": 0.0,
        "fcf_base": 120.0,
        "fcf_is_net_income_proxy": False,
        "assumptions": {field: value},
        "flags": [],
    }
    with pytest.raises(ValidationError, match=field):
        if path == "dictionary":
            IntrinsicValueResult.model_validate(raw)
        else:
            IntrinsicValueResult.model_validate_json(json.dumps(raw))


def _history(values: tuple[float, float] = (100.0, 120.0)) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="SYNTH",
        cik=1,
        entity_name="Synthetic DCF",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid",
        years=tuple(
            AnnualFundamentals(
                fiscal_year=2023 + i,
                period_end=date(2023 + i, 12, 31),
                revenue=1000.0,
                net_income=value,
                free_cash_flow=value,
                shares_diluted=10.0,
                eps=1.0,
            )
            for i, value in enumerate(values)
        ),
    )


@pytest.mark.parametrize(
    ("field", "values", "default_growth"),
    [("max_growth", (100.0, 120.0), 0.12), ("min_growth", (120.0, 100.0), 0.0)],
)
def test_actual_bound_witness_refuses_invalid_configuration_before_use(
    field: str, values: tuple[float, float], default_growth: float
) -> None:
    history = _history(values)
    assert dcf_intrinsic_value(history).growth_rate_used == default_growth
    with pytest.raises(ValidationError, match=field):
        dcf_intrinsic_value(history, DcfAssumptions(**{field: float("nan")}))


@given(
    terminal=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    spread=st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
    low=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    high=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    years=st.integers(min_value=-3, max_value=20),
)
def test_finite_dcf_settings_keep_exact_json_roundtrip(
    terminal: float, spread: float, low: float, high: float, years: int
) -> None:
    settings = DcfAssumptions(
        discount_rate=terminal + spread,
        terminal_growth=terminal,
        min_growth=low,
        max_growth=high,
        projection_years=years,
    )
    payload = settings.model_dump_json()
    assert DcfAssumptions.model_validate_json(payload).model_dump_json() == payload
    assert json.loads(payload) == settings.model_dump()


def test_default_dcf_settings_remain_exact() -> None:
    assert DcfAssumptions().model_dump() == {
        "discount_rate": 0.10,
        "terminal_growth": 0.025,
        "projection_years": 5,
        "max_growth": 0.12,
        "min_growth": 0.0,
    }


def test_finite_coercions_and_inverted_bounds_remain_supported() -> None:
    settings = DcfAssumptions.model_validate(
        {
            "discount_rate": "0.1",
            "terminal_growth": "0.025",
            "min_growth": "0.5",
            "max_growth": "-0.0",
            "projection_years": "0",
        }
    )
    assert settings.min_growth == 0.5
    assert settings.max_growth == 0.0
    assert settings.projection_years == 0
    assert '"max_growth":-0.0' in settings.model_dump_json()


@pytest.mark.parametrize("years", [-2, 0, 1, 5])
def test_existing_projection_year_domain_is_unchanged(years: int) -> None:
    assert DcfAssumptions(projection_years=years).projection_years == years


@pytest.mark.parametrize("rate", [0.01, 0.025])
def test_existing_discount_terminal_relation_still_refuses(rate: float) -> None:
    with pytest.raises(ValidationError, match="discount_rate must exceed terminal_growth"):
        DcfAssumptions(discount_rate=rate, terminal_growth=0.025)


@pytest.mark.parametrize("kind", ["value", "hunt"])
def test_finite_custom_assumptions_reach_actual_provider_valuation(kind: str) -> None:
    settings = DcfAssumptions(terminal_growth=0.0, min_growth=0.0, max_growth=0.0)
    history = _history()
    closes = [(date(2023, 12, 29), 100.0), (date(2024, 12, 30), 100.0)]
    if kind == "value":
        provider = make_value_provider(lambda _: history, lambda _: closes, assumptions=settings)
    else:
        frame = pd.DataFrame(
            {"close": [100.0, 100.0]}, index=pd.to_datetime([d for d, _ in closes], utc=True)
        )
        provider = make_hunt_value_provider(
            lambda _: history, lambda _: frame, assumptions=settings
        )
    score = provider("SYNTH")
    assert score is not None
    # Zero growth/terminal growth gives the independent flat perpetuity FCF/r/shares.
    assert score.intrinsic_value_per_share == pytest.approx(120.0 / 0.10 / 10.0)
    assert score.growth_rate_used == 0.0
