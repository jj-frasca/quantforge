"""Deep immutability and internal identity of cross-sectional claims (ADR-145)."""

import operator
from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.data.models import DataQualityIssue, DataQualityReport
from app.research.backtesting.manifest import compute_parameter_hash
from app.research.claim_graph import FrozenClaimDict, FrozenClaimList
from app.research.cross_sectional.manifest import (
    CrossSectionalManifest,
    PanelComponentManifest,
)
from app.research.cross_sectional.search import (
    CrossSectionalExperiment,
    CrossSectionalTrial,
)
from app.research.lab.experiment import Graduate
from app.research.lab.gate import GateConfig, GateResult


def _claim() -> tuple[
    CrossSectionalExperiment,
    CrossSectionalTrial,
    GateResult,
    Graduate,
    CrossSectionalManifest,
    DataQualityReport,
]:
    experiment_id = uuid4()
    report_id = uuid4()
    created_at = datetime(2026, 9, 28, tzinfo=UTC)
    config = GateConfig()
    gate_result = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version=config.version_hash,
        reasons=["original verdict"],
        holdout_sharpe=1.0,
        holdout_n_bars=100,
    )
    trial = CrossSectionalTrial(
        strategy_name="xs_momentum",
        parameters={"lookback": 20, "quantile": 0.2},
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    graduate = Graduate(
        strategy_name="xs_momentum",
        parameters={"lookback": 20, "quantile": 0.2},
        gate_result=gate_result,
        holdout_sharpe=1.0,
        holdout_total_return=0.1,
        holdout_n_bars=100,
    )
    report = DataQualityReport(
        id=report_id,
        symbol="A",
        source="yfinance",
        checked_at=created_at,
        issues=[
            DataQualityIssue(
                check="price_anomaly",
                severity="warning",
                message="flags potential price anomaly",
                context={"observed": [0.25]},
            )
        ],
    )
    component = PanelComponentManifest(
        symbol="A",
        data_source="yfinance",
        adapter_version="test-v1",
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1),
        data_quality_report_id=report_id,
    )
    manifest = CrossSectionalManifest(
        experiment_id=experiment_id,
        created_at=created_at,
        git_commit_hash="a" * 40,
        strategy_name="xs_momentum",
        parameter_hash=compute_parameter_hash(trial.parameters),
        validation_config_hash=config.version_hash,
        components=[component],
    )
    experiment = CrossSectionalExperiment(
        experiment_id=experiment_id,
        created_at=created_at,
        universe_symbols=["A"],
        strategy_names=["xs_momentum"],
        gate_config=config,
        trials=[trial],
        lifetime_trials=1,
        best_strategy_name="xs_momentum",
        best_gate_result=gate_result,
        graduate=graduate,
        panel_manifest=manifest,
        data_quality_reports=[report],
    )
    return experiment, trial, gate_result, graduate, manifest, report


def test_experiment_claim_graph_is_defensive_immutable_and_round_trips() -> None:
    experiment, trial, gate_result, graduate, manifest, report = _claim()
    before = experiment.model_dump(mode="json")

    # Mutating caller-owned nested models after construction must not alter the durable claim.
    trial.parameters["lookback"] = 999
    gate_result.reasons.append("caller mutation")
    graduate.parameters["quantile"] = 0.49
    manifest.components.append(manifest.components[0])
    assert report.issues[0].context is not None
    report.issues[0].context["observed"] = [999.0]
    assert experiment.model_dump(mode="json") == before

    # The public graph itself must expose no in-place mutation surface.
    with pytest.raises(AttributeError):
        experiment.universe_symbols.append("B")
    with pytest.raises(AttributeError):
        experiment.strategy_names.append("xs_reversal")
    with pytest.raises(AttributeError):
        experiment.trials.append(experiment.trials[0])
    with pytest.raises(TypeError, match="immutable"):
        experiment.trials[0].parameters["lookback"] = 999
    assert experiment.best_gate_result is not None
    with pytest.raises(AttributeError):
        experiment.best_gate_result.reasons.append("public mutation")
    assert experiment.graduate is not None
    with pytest.raises(TypeError, match="immutable"):
        experiment.graduate.parameters["quantile"] = 0.49
    with pytest.raises(AttributeError):
        experiment.graduate.gate_result.reasons.append("nested mutation")
    assert experiment.panel_manifest is not None
    with pytest.raises(AttributeError):
        experiment.panel_manifest.components.append(experiment.panel_manifest.components[0])
    assert experiment.data_quality_reports is not None
    with pytest.raises(AttributeError):
        experiment.data_quality_reports.append(experiment.data_quality_reports[0])
    with pytest.raises(AttributeError):
        experiment.data_quality_reports[0].issues.append(
            experiment.data_quality_reports[0].issues[0]
        )
    context = experiment.data_quality_reports[0].issues[0].context
    assert context is not None
    with pytest.raises(TypeError, match="immutable"):
        context["observed"] = [999.0]
    with pytest.raises(AttributeError):
        context["observed"].append(999.0)  # type: ignore[union-attr]

    restored = CrossSectionalExperiment.model_validate_json(experiment.model_dump_json())
    assert restored == experiment
    assert restored.model_dump(mode="json") == before


def test_experiment_rejects_strategy_and_graduate_identity_drift() -> None:
    experiment, *_ = _claim()
    strategy_drift = experiment.model_dump(mode="json")
    strategy_drift["strategy_names"] = ["xs_reversal"]
    with pytest.raises(ValidationError, match="strategy_names must exactly match"):
        CrossSectionalExperiment.model_validate(strategy_drift)

    graduate_drift = experiment.model_dump(mode="json")
    graduate_drift["graduate"]["parameters"]["quantile"] = 0.3
    with pytest.raises(ValidationError, match="graduate parameters must match"):
        CrossSectionalExperiment.model_validate(graduate_drift)


def test_experiment_rejects_gate_result_identity_drift() -> None:
    experiment, *_ = _claim()
    payload = experiment.model_dump(mode="json")
    payload["graduate"]["gate_result"]["holdout_sharpe"] = 2.0

    with pytest.raises(ValidationError, match="graduate gate result must match"):
        CrossSectionalExperiment.model_validate(payload)


def test_experiment_rejects_every_selected_graduate_relationship_drift() -> None:
    experiment, *_ = _claim()
    original = experiment.model_dump(mode="json")

    payload = deepcopy(original)
    payload["best_strategy_name"] = "xs_reversal"
    with pytest.raises(ValidationError, match="best_strategy_name must identify"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["best_strategy_name"] = None
    with pytest.raises(ValidationError, match="graduate requires the selected"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["best_gate_result"] = None
    with pytest.raises(ValidationError, match="graduate requires the best gate"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["strategy_name"] = "xs_reversal"
    with pytest.raises(ValidationError, match="graduate strategy must match"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["best_gate_result"]["passed"] = False
    payload["graduate"]["gate_result"]["passed"] = False
    with pytest.raises(ValidationError, match="graduate requires a passing"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["holdout_sharpe"] = 2.0
    with pytest.raises(ValidationError, match="graduate holdout Sharpe must match"):
        CrossSectionalExperiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["holdout_n_bars"] = 101
    with pytest.raises(ValidationError, match="graduate holdout length must match"):
        CrossSectionalExperiment.model_validate(payload)


def test_frozen_claim_list_rejects_every_ordinary_mutator() -> None:
    mutations = (
        lambda value: operator.setitem(value, 0, 3),
        lambda value: operator.delitem(value, 0),
        lambda value: operator.iadd(value, [3]),
        lambda value: operator.imul(value, 2),
        lambda value: value.append(3),
        lambda value: value.clear(),
        lambda value: value.extend([3]),
        lambda value: value.insert(0, 3),
        lambda value: value.pop(),
        lambda value: value.remove(1),
        lambda value: value.reverse(),
        lambda value: value.sort(),
    )

    for mutate in mutations:
        with pytest.raises(AttributeError, match="immutable"):
            mutate(FrozenClaimList([1, 2]))


def test_frozen_claim_dict_rejects_every_ordinary_mutator() -> None:
    mutations = (
        lambda value: operator.setitem(value, "a", 2),
        lambda value: operator.delitem(value, "a"),
        lambda value: operator.ior(value, {"b": 2}),
        lambda value: value.clear(),
        lambda value: value.pop("a"),
        lambda value: value.popitem(),
        lambda value: value.setdefault("b", 2),
        lambda value: value.update({"b": 2}),
    )

    for mutate in mutations:
        with pytest.raises(TypeError, match="immutable"):
            mutate(FrozenClaimDict({"a": 1}))
