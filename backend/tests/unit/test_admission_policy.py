"""ADR-375: surviving-row effective rubrics are explicit, canonical and defensive."""

import importlib
import importlib.util
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError
from tests.unit.test_universe_valuation_resilience import _dataset, _score

from app.research.fundamentals.record import FundamentalRecord
from app.research.lab import universe
from app.research.lab.experiment import (
    Experiment,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    Trial,
)
from app.research.lab.gate import GateConfig
from app.research.lab.quality_filter import QualityGateConfig
from app.research.lab.value_filter import ValueGateConfig


def _policy_type() -> type[BaseModel]:
    name = "app.research.lab.admission_policy"
    assert importlib.util.find_spec(name) is not None, (
        "AdmissionPolicy evidence boundary is missing"
    )
    return importlib.import_module(name).AdmissionPolicy


def _experiment() -> Experiment:
    return Experiment(
        experiment_id=UUID(int=1),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        symbol="GOOD",
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={},
                observed_sharpe=0.1,
                deflated_sharpe=0.0,
                pbo=0.5,
                parameter_stability_score=0.5,
            )
        ],
        lifetime_trials=1,
        best_strategy_name="sma",
        selected_trial_index=0,
    )


def _quality(_symbol: str) -> FundamentalRecord:
    return FundamentalRecord(
        symbol="GOOD",
        cik=1,
        fiscal_year=2025,
        quality_score=0.9,
        value_score=None,
        combined_score=None,
        f_score=9,
        gross_profitability=0.1,
    )


@pytest.mark.parametrize("vp,vc,qp,qc", list(itertools.product([False, True], repeat=4)))
def test_hunt_records_only_effective_screen_pairs(
    monkeypatch: pytest.MonkeyPatch, vp: bool, vc: bool, qp: bool, qc: bool
) -> None:
    search = Mock(return_value=_experiment())
    monkeypatch.setattr(universe, "run_search", search)
    values = Mock(side_effect=_score)
    qualities = Mock(side_effect=_quality)
    store = InMemoryExperimentStore()
    value_config = ValueGateConfig(
        min_score=0.7, keep_unscored=False, require_margin_of_safety=True
    )
    quality_config = QualityGateConfig(min_quality_score=0.6, min_f_score=8, keep_unscored=False)
    result = universe.run_universe_hunt(
        ["GOOD"],
        ["sma"],
        _dataset,
        value_provider=values if vp else None,
        value_config=value_config if vc else None,
        quality_provider=qualities if qp else None,
        quality_config=quality_config if qc else None,
        store=store,
    )
    assert result.errors == result.filtered == {}
    row = store.all()[0]
    assert "admission_policy" in row.model_dump()
    policy = row.admission_policy
    assert policy is not None
    assert policy.value_config == (value_config if vp and vc else None)
    assert policy.quality_config == (quality_config if qp and qc else None)
    assert values.call_count == int(vp)
    assert qualities.call_count == int(qp and qc)
    assert row.gate_config.version_hash == _experiment().gate_config.version_hash
    assert row.manifest is not None
    assert row.manifest.validation_config_hash == row.gate_config.version_hash


def test_distinct_surviving_rubrics_differ_only_in_admission_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(universe, "run_search", Mock(return_value=_experiment()))
    payloads = []
    hashes = []
    for minimum in [None, 0.2, 0.7]:
        store = InMemoryExperimentStore()
        result = universe.run_universe_hunt(
            ["GOOD"],
            ["sma"],
            _dataset,
            value_provider=_score,
            value_config=None if minimum is None else ValueGateConfig(min_score=minimum),
            quality_provider=_quality,
            quality_config=None
            if minimum is None
            else QualityGateConfig(min_quality_score=minimum),
            store=store,
        )
        assert not result.errors
        row = store.all()[0]
        payload = row.model_dump(mode="json")
        assert "admission_policy" in payload
        policy = payload.pop("admission_policy")
        assert policy is not None
        payloads.append(payload)
        hashes.append(
            row.admission_policy.value_config.version_hash
            if row.admission_policy.value_config is not None
            else None
        )
    assert payloads[0] == payloads[1] == payloads[2]
    assert len(set(hashes)) == 3


@pytest.mark.parametrize("payload", [{}, {"value_config": None}, {"quality_config": None}])
def test_present_policy_requires_both_nullable_keys(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _policy_type().model_validate(payload)


@pytest.mark.parametrize("legacy", [True, False])
def test_old_and_direct_experiment_rubrics_remain_unknown(legacy: bool) -> None:
    payload = _experiment().model_dump()
    if legacy:
        payload.pop("admission_policy", None)
    restored = Experiment.model_validate(payload)
    assert "admission_policy" in restored.model_dump()
    assert restored.admission_policy is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("keep_unscored", "false"),
        ("min_score", 1),
        ("min_score", float("nan")),
        ("min_score", float("inf")),
        ("min_score", np.float32(0.5)),
    ],
)
def test_policy_refuses_noncanonical_unchecked_config(field: str, value: object) -> None:
    config = ValueGateConfig().model_copy(update={field: value})
    with pytest.raises((ValidationError, TypeError, ValueError)):
        _policy_type()(value_config=config, quality_config=None)


@pytest.mark.parametrize("change", ["missing", "extra", "integer", "string_bool"])
def test_policy_json_refuses_silent_config_normalization(change: str) -> None:
    raw = ValueGateConfig().model_dump()
    if change == "missing":
        raw.pop("keep_unscored")
    elif change == "extra":
        raw["unknown"] = True
    elif change == "integer":
        raw["min_score"] = 1
    else:
        raw["keep_unscored"] = "false"
    with pytest.raises(ValidationError):
        _policy_type().model_validate_json(
            json.dumps({"value_config": raw, "quality_config": None})
        )


def test_policy_preserves_ordinary_coercions_and_json_equivalent_values() -> None:
    value = ValueGateConfig(min_score=1, keep_unscored="false")
    quality = QualityGateConfig(min_quality_score=np.float32(0.3), min_f_score=8)
    policy = _policy_type()(value_config=value, quality_config=quality)
    restored = _policy_type().model_validate_json(policy.model_dump_json())
    assert restored.model_dump() == policy.model_dump()
    assert restored.value_config.version_hash == value.version_hash
    assert restored.quality_config.version_hash == quality.version_hash
    equivalent = value.model_copy(update={"min_score": np.float64(1.0)})
    assert _policy_type()(value_config=equivalent, quality_config=None).value_config == value


def test_policy_and_experiment_defensively_reconstruct_untrusted_instances() -> None:
    value = ValueGateConfig(min_score=0.7)
    policy = _policy_type()(value_config=value, quality_config=None)
    row = Experiment.model_validate({**_experiment().model_dump(), "admission_policy": policy})
    object.__setattr__(value, "min_score", 0.1)
    object.__setattr__(policy.value_config, "min_score", 0.2)
    assert row.admission_policy.value_config.min_score == 0.7
    with pytest.raises(ValidationError, match="frozen"):
        row.admission_policy.value_config.min_score = 0.4
    invalid = policy.model_copy(
        update={"value_config": ValueGateConfig().model_copy(update={"keep_unscored": "false"})}
    )
    with pytest.raises(ValidationError):
        _policy_type().model_validate(invalid)
    with pytest.raises(ValidationError):
        Experiment.model_validate({**row.model_dump(), "admission_policy": invalid})


@pytest.mark.parametrize("kind", ["memory", "json", "partitioned"])
def test_admission_policy_survives_store_roundtrip_and_refuses_invalid_write(
    tmp_path: Path,
    kind: str,
) -> None:
    store = (
        InMemoryExperimentStore()
        if kind == "memory"
        else JsonFileExperimentStore(tmp_path / "pool.json")
        if kind == "json"
        else PartitionedExperimentStore(tmp_path / "pool")
    )
    policy = _policy_type()(value_config=ValueGateConfig(min_score=0.7), quality_config=None)
    row = Experiment.model_validate({**_experiment().model_dump(), "admission_policy": policy})
    store.add(row)
    assert store.all()[0].admission_policy.model_dump_json() == policy.model_dump_json()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.json")}
    invalid_policy = policy.model_copy(
        update={"value_config": ValueGateConfig().model_copy(update={"keep_unscored": "false"})}
    )
    with pytest.raises(ValidationError):
        store.add(row.model_copy(update={"admission_policy": invalid_policy}))
    assert len(store.all()) == 1
    assert {p: p.read_bytes() for p in tmp_path.rglob("*.json")} == before


def test_active_noncanonical_snapshot_refuses_after_search_and_inactive_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = Mock(return_value=_experiment())
    monkeypatch.setattr(universe, "run_search", search)
    # ValueScreen parses 'true' as passed, but the runtime rubric is not canonical evidence.
    invalid = ValueGateConfig().model_copy(update={"keep_unscored": "true"})
    result = universe.run_universe_hunt(
        ["GOOD"], ["sma"], _dataset, value_provider=lambda _: None, value_config=invalid
    )
    assert result.experiments == []
    assert set(result.errors) == {"GOOD"}
    assert search.call_count == 1
    result = universe.run_universe_hunt(["GOOD"], ["sma"], _dataset, value_config=invalid)
    assert result.errors == {}
    assert result.experiments[0].admission_policy.value_config is None


def test_falsey_value_provider_keeps_existing_is_not_none_screen_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FalseyProvider:
        def __bool__(self) -> bool:
            return False

        def __call__(self, _symbol: str) -> None:
            raise AssertionError("existing value acquisition skips falsey providers")

    monkeypatch.setattr(universe, "run_search", Mock(return_value=_experiment()))
    result = universe.run_universe_hunt(
        ["GOOD"], ["sma"], _dataset, value_provider=FalseyProvider(), value_config=ValueGateConfig()
    )
    assert result.errors == {}
    assert result.experiments[0].admission_policy.value_config == ValueGateConfig()


def test_unchecked_false_string_still_filters_before_snapshot_attachment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = Mock(side_effect=AssertionError("filtered name must not reach search"))
    monkeypatch.setattr(universe, "run_search", search)
    result = universe.run_universe_hunt(
        ["GOOD"],
        ["sma"],
        _dataset,
        value_provider=lambda _: None,
        value_config=ValueGateConfig().model_copy(update={"keep_unscored": "false"}),
    )
    assert result.errors == {}
    assert result.experiments == []
    assert "GOOD" in result.filtered
    search.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("keep_unscored", "true"),
        ("min_quality_score", 1),
        ("min_f_score", 8.0),
        ("min_quality_score", float("inf")),
    ],
)
def test_quality_snapshot_refuses_noncanonical_unchecked_config(field: str, value: object) -> None:
    config = QualityGateConfig().model_copy(update={field: value})
    with pytest.raises((ValidationError, TypeError, ValueError)):
        _policy_type()(value_config=None, quality_config=config)


@settings(max_examples=40)
@given(minimum=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_rubric_snapshot_keeps_exact_minima_and_hashes(minimum: float) -> None:
    value = ValueGateConfig(min_score=minimum)
    quality = QualityGateConfig(min_quality_score=minimum)
    policy = _policy_type()(value_config=value, quality_config=quality)
    restored = _policy_type().model_validate_json(policy.model_dump_json())
    assert restored.value_config.min_score.hex() == minimum.hex()
    assert restored.quality_config.min_quality_score.hex() == minimum.hex()
    assert restored.value_config.version_hash == value.version_hash
    assert restored.quality_config.version_hash == quality.version_hash
