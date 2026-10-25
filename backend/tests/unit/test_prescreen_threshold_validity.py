"""ADR-372: malformed minima cannot define optional universe pre-screens."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from app.research.lab.quality_filter import QualityGateConfig, parse_quality_screen
from app.research.lab.value_filter import ValueGateConfig
from app.research.lab.value_wiring import parse_value_screen

CONFIGS = [(QualityGateConfig, "min_quality_score"), (ValueGateConfig, "min_score")]


@pytest.mark.parametrize(("config_type", "field"), CONFIGS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "nan", "inf", "-inf"])
@pytest.mark.parametrize("via_json", [False, True])
def test_optional_prescreen_config_refuses_nonfinite_minimum(
    config_type: type[BaseModel], field: str, value: object, via_json: bool
) -> None:
    payload = {field: value}
    with pytest.raises(ValidationError, match=field):
        if via_json:
            config_type.model_validate_json(json.dumps(payload))
        else:
            config_type(**payload)


@pytest.mark.parametrize("name", ["quality", "value"])
@pytest.mark.parametrize("token", ["nan", "NaN", "inf", "+Infinity", "-inf", "-Infinity"])
def test_optional_prescreen_cli_refuses_nonfinite_numeric_override(name: str, token: str) -> None:
    parse = parse_quality_screen if name == "quality" else parse_value_screen
    with pytest.raises(ValidationError):
        parse([f"--{name}-screen", token, "LOW"])


@pytest.mark.parametrize(("config_type", "field"), CONFIGS)
@settings(max_examples=40, deadline=None)
@given(threshold=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_prescreen_minimum_retains_exact_value_and_hash_on_json_round_trip(
    config_type: type[BaseModel], field: str, threshold: float
) -> None:
    config = config_type(**{field: threshold})
    restored = config_type.model_validate_json(config.model_dump_json())
    assert getattr(config, field).hex() == threshold.hex()
    assert getattr(restored, field).hex() == threshold.hex()
    assert restored.version_hash == config.version_hash


@pytest.mark.parametrize("name", ["quality", "value"])
def test_optional_prescreen_stays_disabled_without_flag(name: str) -> None:
    parse = parse_quality_screen if name == "quality" else parse_value_screen
    assert parse(["LOW"]) == (None, ["LOW"])
