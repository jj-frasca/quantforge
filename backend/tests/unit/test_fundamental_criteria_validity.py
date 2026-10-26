"""ADR-377: enabled fundamental checks require finite configuration minima."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import (
    FundamentalCriteria,
    FundamentalSnapshot,
    screen_fundamentals,
)

FIELDS = ("min_revenue_growth_yoy", "min_net_margin")


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "nan", "inf", "-inf"])
@pytest.mark.parametrize("via_json", [False, True])
def test_fundamental_criteria_refuses_nonfinite_enabled_minimum(
    field: str, value: object, via_json: bool
) -> None:
    payload = {field: value}
    with pytest.raises(ValidationError, match=field):
        if via_json:
            FundamentalCriteria.model_validate_json(json.dumps(payload))
        else:
            FundamentalCriteria.model_validate(payload)


@pytest.mark.parametrize("field", FIELDS)
@settings(max_examples=50, deadline=None)
@given(threshold=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_fundamental_minimum_preserves_exact_json_round_trip(
    field: str, threshold: float
) -> None:
    config = FundamentalCriteria.model_validate({field: threshold})
    restored = FundamentalCriteria.model_validate_json(config.model_dump_json())
    assert getattr(config, field).hex() == threshold.hex()
    assert getattr(restored, field).hex() == threshold.hex()
    assert restored == config


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [-1e300, 1e300, "-0.25", 1])
def test_fundamental_criteria_keeps_finite_values_and_coercions(
    field: str, value: float | str
) -> None:
    config = FundamentalCriteria.model_validate({field: value})
    assert getattr(config, field) == float(value)


def _negative_snapshot() -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol="SYNTH",
        cik=1,
        entity_name="Synthetic",
        fiscal_year=2024,
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid",
        revenue=100.0,
        revenue_growth_yoy=-0.5,
        net_margin=-0.5,
    )


def test_fundamental_criteria_defaults_keep_both_negative_metric_failures() -> None:
    config = FundamentalCriteria()
    assert config.min_revenue_growth_yoy == 0.0
    assert config.min_net_margin == 0.0
    result = screen_fundamentals(_negative_snapshot(), config)
    assert result.passed is False
    assert result.reasons == ["revenue growth -50.0% < 0.0%", "net margin -50.0% < 0.0%"]


@pytest.mark.parametrize("disabled", [(True, False), (False, True), (True, True)])
def test_none_fundamental_minimum_keeps_deliberate_check_disablement(
    disabled: tuple[bool, bool],
) -> None:
    config = FundamentalCriteria(
        min_revenue_growth_yoy=None if disabled[0] else 0.0,
        min_net_margin=None if disabled[1] else 0.0,
    )
    result = screen_fundamentals(_negative_snapshot(), config)
    assert result.passed is all(disabled)
    assert len(result.reasons) == 2 - sum(disabled)
    assert FundamentalCriteria.model_validate_json(config.model_dump_json()) == config
