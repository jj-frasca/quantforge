"""ADR-402: retain resolved backend settings without inventing legacy defaults."""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.unit.test_experiment_store import _experiment
from tests.unit.test_valuation_multiples import _three_year
from tests.unit.test_valuation_score import _rich

from app.research.lab.experiment import (
    Experiment,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
)
from app.research.lab.value_filter import make_value_provider
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.score import UndervaluationScore, score_valuation

SETTINGS = [
    DcfAssumptions(),
    DcfAssumptions(max_growth=0.3),
    DcfAssumptions(projection_years=0),
    DcfAssumptions(projection_years=-2),
    DcfAssumptions(min_growth=0.3, max_growth=-0.1),
    DcfAssumptions(max_growth="0.2", projection_years="2"),
]


@pytest.mark.parametrize("settings", SETTINGS)
@pytest.mark.parametrize("available", [False, True])
def test_actual_resolved_settings_retained_including_unsuccessful_dcf(settings, available) -> None:
    history = _rich() if available else _three_year()
    intrinsic = dcf_intrinsic_value(history, settings)
    score = score_valuation(history, 55.0, assumptions=settings)
    assert getattr(score, "dcf_assumptions", None) == intrinsic.assumptions
    assert score.dcf_assumptions is not settings
    assert score.intrinsic_value_per_share == intrinsic.intrinsic_value_per_share
    assert UndervaluationScore.model_validate_json(score.model_dump_json()) == score


def test_default_is_resolved_and_distinct_unused_caps_are_no_longer_erased() -> None:
    default = score_valuation(_rich(), 55.0)
    assert getattr(default, "dcf_assumptions", None) == DcfAssumptions()
    left = score_valuation(_rich(), 55.0, assumptions=DcfAssumptions(max_growth=0.2))
    right = score_valuation(_rich(), 55.0, assumptions=DcfAssumptions(max_growth=0.3))
    assert left.model_dump_json() != right.model_dump_json()
    assert left.model_dump(exclude={"dcf_assumptions"}) == right.model_dump(
        exclude={"dcf_assumptions"}
    )


@pytest.mark.parametrize("explicit_null", [False, True])
def test_legacy_unknown_omission_never_infers_defaults(explicit_null: bool) -> None:
    raw = score_valuation(_rich(), 55.0).model_dump(round_trip=True, exclude={"dcf_assumptions"})
    legacy = UndervaluationScore.model_validate(
        {**raw, **({"dcf_assumptions": None} if explicit_null else {})}
    )
    assert getattr(legacy, "dcf_assumptions", None) is None
    assert legacy.model_dump(round_trip=True) == raw
    assert "dcf_assumptions" not in legacy.model_dump_json()


@pytest.mark.parametrize(
    "update",
    [
        {"max_growth": 1},
        {"max_growth": "0.2"},
        {"projection_years": True},
        {"max_growth": float("nan")},
        {"min_growth": float("inf")},
        {"discount_rate": 0.01},
    ],
)
def test_unchecked_nested_settings_cannot_be_reinterpreted_or_invalid(update: dict) -> None:
    raw = score_valuation(_rich(), 55.0).model_dump(round_trip=True, exclude={"dcf_assumptions"})
    forged = DcfAssumptions().model_copy(update=update)
    with pytest.raises(ValueError):
        UndervaluationScore.model_validate({**raw, "dcf_assumptions": forged})


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"max_growth": 0.3},
        {**DcfAssumptions().model_dump(), "extra": 1},
        {**DcfAssumptions().model_dump(), "max_growth": 1},
        {**DcfAssumptions().model_dump(), "projection_years": True},
    ],
)
def test_raw_mapping_requires_complete_canonical_settings(raw: dict) -> None:
    payload = score_valuation(_rich(), 55.0).model_dump(
        round_trip=True, exclude={"dcf_assumptions"}
    )
    with pytest.raises(ValueError):
        UndervaluationScore.model_validate({**payload, "dcf_assumptions": raw})


def test_snapshot_detaches_caller_model_and_raw_mapping_and_is_frozen() -> None:
    settings = DcfAssumptions(max_growth=0.3)
    score = score_valuation(_rich(), 55.0, assumptions=settings)
    assert getattr(score, "dcf_assumptions", None) == settings
    assert score.dcf_assumptions is not settings
    with pytest.raises(ValidationError, match="frozen"):
        score.dcf_assumptions.max_growth = 0.7
    payload = score.model_dump(round_trip=True)
    restored = UndervaluationScore.model_validate(payload)
    payload["dcf_assumptions"]["max_growth"] = 0.9
    assert restored.dcf_assumptions.max_growth == 0.3


def test_unconsumed_unchecked_setting_now_refuses_after_dcf_early_return() -> None:
    h = _three_year()
    forged = DcfAssumptions().model_copy(update={"max_growth": "0.2"})
    assert dcf_intrinsic_value(h, forged).intrinsic_value_per_share is None
    with pytest.raises(ValueError, match="canonical JSON"):
        score_valuation(h, 55.0, assumptions=forged)


def test_earlier_operand_refusal_still_precedes_bad_snapshot() -> None:
    h = _three_year()
    h = h.model_copy(
        update={"years": (*h.years[:-1], h.years[-1].model_copy(update={"eps": float("inf")}))}
    )
    forged = DcfAssumptions().model_copy(update={"max_growth": "0.2"})
    with pytest.raises(ValueError, match="current P/E EPS operand must be finite"):
        score_valuation(h, 55.0, assumptions=forged)


def test_real_provider_preserves_actual_settings_without_services() -> None:
    settings = DcfAssumptions(max_growth=0.3)
    h = _rich()
    provider = make_value_provider(
        lambda symbol: h, lambda symbol: [(date(2025, 12, 31), 55.0)], assumptions=settings
    )
    result = provider(h.symbol)
    assert result is not None and getattr(result, "dcf_assumptions", None) == settings


@pytest.mark.parametrize(
    "store_type", [InMemoryExperimentStore, JsonFileExperimentStore, PartitionedExperimentStore]
)
def test_experiment_and_all_backend_stores_preserve_snapshot(store_type, tmp_path) -> None:
    score = score_valuation(_rich(), 55.0, assumptions=DcfAssumptions(max_growth=0.3))
    exp = Experiment.model_validate(
        {**_experiment("AAPL", 1).model_dump(round_trip=True), "undervaluation_score": score}
    )
    assert getattr(exp.undervaluation_score, "dcf_assumptions", None) == DcfAssumptions(
        max_growth=0.3
    )
    store = (
        store_type()
        if store_type is InMemoryExperimentStore
        else store_type(tmp_path / "scratch-pool")
    )
    store.add(exp)
    reader = (
        store if store_type is InMemoryExperimentStore else store_type(tmp_path / "scratch-pool")
    )
    loaded = reader.all()[0]
    assert loaded == exp
    assert loaded.undervaluation_score.dcf_assumptions == score.dcf_assumptions
    assert Experiment.model_validate_json(loaded.model_dump_json()) == exp


def test_existing_experiment_reconstruction_refuses_forged_nested_snapshot() -> None:
    score = score_valuation(_rich(), 55.0).model_copy(
        update={"dcf_assumptions": DcfAssumptions().model_copy(update={"projection_years": True})}
    )
    with pytest.raises(ValueError):
        Experiment.model_validate(
            {**_experiment("AAPL", 1).model_dump(round_trip=True), "undervaluation_score": score}
        )


@given(
    max_growth=st.floats(min_value=-0.5, max_value=0.5),
    min_growth=st.floats(min_value=-0.5, max_value=0.5),
    horizon=st.integers(min_value=-2, max_value=8),
)
def test_finite_settings_snapshot_roundtrips_exactly(
    max_growth: float, min_growth: float, horizon: int
) -> None:
    settings = DcfAssumptions(
        max_growth=max_growth, min_growth=min_growth, projection_years=horizon
    )
    score = score_valuation(_rich(), 55.0, assumptions=settings)
    assert getattr(score, "dcf_assumptions", None) == settings
    restored = UndervaluationScore.model_validate_json(score.model_dump_json())
    assert restored.dcf_assumptions.model_dump_json() == settings.model_dump_json()
