"""Defensive identity and evidence contracts for shared research leaves (ADR-162)."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.research.lab import experiment as experiment_models
from app.research.lab.experiment import Graduate, Trial
from app.research.lab.gate import GateResult


def _gate(*, passed: bool = True) -> GateResult:
    return GateResult(
        passed=passed,
        dsr_ok=passed,
        pbo_ok=passed,
        stability_ok=passed,
        mintrl_ok=passed,
        holdout_ok=passed,
        beats_buy_and_hold_ok=passed,
        required_track_record_years=1.0,
        gate_config_version="gate-v1",
        reasons=[],
        holdout_sharpe=1.0,
        holdout_n_bars=252,
    )


def _trial(**updates: object) -> Trial:
    payload: dict[str, object] = {
        "strategy_name": "sma",
        "parameters": {"fast": 5, "slow": 20},
        "observed_sharpe": 1.0,
        "deflated_sharpe": 0.5,
        "pbo": 0.1,
        "parameter_stability_score": 0.8,
        "walk_forward_oos_sharpe": 0.3,
        "purged_cv_oos_sharpe": 0.4,
        "deflated_sharpe_probability": 0.9,
    }
    payload.update(updates)
    return Trial.model_validate(payload)


def _graduate(**updates: object) -> Graduate:
    payload: dict[str, object] = {
        "strategy_name": "sma",
        "parameters": {"fast": 5, "slow": 20},
        "gate_result": _gate(),
        "holdout_sharpe": 1.0,
        "holdout_total_return": 0.1,
        "holdout_n_bars": 252,
    }
    payload.update(updates)
    return Graduate.model_validate(payload)


def test_trial_parameters_are_defensive_immutable_and_round_trip() -> None:
    parameters = {"fast": 5, "slow": 20}
    trial = _trial(parameters=parameters)
    before = trial.model_dump(mode="json")

    parameters["fast"] = 999
    assert trial.model_dump(mode="json") == before
    with pytest.raises(TypeError, match="immutable"):
        trial.parameters["fast"] = 999

    restored = Trial.model_validate_json(trial.model_dump_json())
    assert restored == trial
    assert restored.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"strategy_name": ""}, "strategy_name"),
        ({"parameters": {"fast": float("nan")}}, "parameters"),
        ({"parameters": {"fast": float("inf")}}, "parameters"),
        ({"observed_sharpe": float("nan")}, "observed_sharpe"),
        ({"deflated_sharpe": float("inf")}, "deflated_sharpe"),
        ({"pbo": -0.1}, "pbo"),
        ({"pbo": 1.1}, "pbo"),
        ({"parameter_stability_score": -0.1}, "parameter_stability_score"),
        ({"parameter_stability_score": 1.1}, "parameter_stability_score"),
        ({"walk_forward_oos_sharpe": float("nan")}, "walk_forward_oos_sharpe"),
        ({"purged_cv_oos_sharpe": float("inf")}, "purged_cv_oos_sharpe"),
        ({"deflated_sharpe_probability": -0.1}, "deflated_sharpe_probability"),
        ({"deflated_sharpe_probability": 1.1}, "deflated_sharpe_probability"),
    ],
)
def test_trial_rejects_invalid_identity_and_evidence(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _trial(**updates)


def test_graduate_is_defensive_immutable_and_round_trips() -> None:
    parameters = {"fast": 5, "slow": 20}
    graduate = _graduate(parameters=parameters)
    before = graduate.model_dump(mode="json")

    parameters["fast"] = 999
    assert graduate.model_dump(mode="json") == before
    with pytest.raises(TypeError, match="immutable"):
        graduate.parameters["fast"] = 999

    restored = Graduate.model_validate_json(graduate.model_dump_json())
    assert restored == graduate
    assert restored.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"strategy_name": ""}, "strategy_name"),
        ({"parameters": {"fast": float("nan")}}, "parameters"),
        ({"gate_result": _gate(passed=False)}, "passing gate"),
        ({"holdout_sharpe": float("nan")}, "holdout_sharpe"),
        ({"holdout_total_return": float("inf")}, "holdout_total_return"),
        ({"holdout_total_return": -1.0}, "holdout_total_return"),
        ({"holdout_n_bars": 0}, "holdout_n_bars"),
        ({"holdout_sharpe": 2.0}, "holdout Sharpe must match"),
        ({"holdout_n_bars": 253}, "holdout length must match"),
    ],
)
def test_graduate_rejects_invalid_or_incoherent_evidence(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _graduate(**updates)


def test_validated_trial_update_rejects_unchecked_values_and_preserves_subtype() -> None:
    from app.research.cross_sectional.search import CrossSectionalTrial

    trial = CrossSectionalTrial(**_trial().model_dump(), ic=None)
    payload = deepcopy(trial.model_dump(round_trip=True))

    with pytest.raises(ValidationError, match="deflated_sharpe"):
        experiment_models.validated_trial_update(
            trial,
            {"deflated_sharpe": float("nan")},
        )

    updated = experiment_models.validated_trial_update(
        trial,
        {"deflated_sharpe": 0.25, "pbo": 0.2},
    )
    assert isinstance(updated, CrossSectionalTrial)
    assert updated.deflated_sharpe == 0.25
    assert updated.pbo == 0.2
    assert payload["observed_sharpe"] == updated.observed_sharpe
