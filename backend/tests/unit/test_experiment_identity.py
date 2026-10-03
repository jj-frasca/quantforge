"""Deep immutability and internal identity of single-name claims (ADR-147)."""

from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.data.fundamentals import FundamentalScreen, FundamentalSnapshot
from app.data.models import DataQualityIssue, DataQualityReport
from app.research.backtesting.manifest import ExperimentManifest, compute_parameter_hash
from app.research.fundamentals.distress import DistressScreen
from app.research.lab.experiment import Experiment, Graduate, Trial, selected_trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.valuation import UndervaluationScore


def _claim() -> tuple[
    Experiment,
    Trial,
    GateResult,
    Graduate,
    DataQualityReport,
    FundamentalScreen,
    DistressScreen,
    UndervaluationScore,
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
    trial = Trial(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    graduate = Graduate(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        gate_result=gate_result,
        holdout_sharpe=1.0,
        holdout_total_return=0.1,
        holdout_n_bars=100,
    )
    report = DataQualityReport(
        id=report_id,
        symbol="AAPL",
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
    manifest = ExperimentManifest(
        experiment_id=experiment_id,
        created_at=created_at,
        git_commit_hash="a" * 40,
        strategy_name="sma",
        parameter_hash=compute_parameter_hash(trial.parameters),
        data_source="yfinance",
        symbol="AAPL",
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1),
        data_quality_report_id=report_id,
        adapter_version="test-v1",
        validation_config_hash=config.version_hash,
    )
    fundamentals = FundamentalSnapshot(
        symbol="AAPL",
        cik=1,
        entity_name="Apple",
        fiscal_year=2025,
        form="10-K",
        accession_number="test",
        source_url="https://example.test/filing",
        revenue=100.0,
        revenue_growth_yoy=0.1,
        net_margin=0.2,
    )
    fundamental_screen = FundamentalScreen(passed=True, reasons=["reviewed"])
    distress_screen = DistressScreen(distressed=False, reasons=["reviewed"])
    valuation = UndervaluationScore(
        symbol="AAPL",
        cik=1,
        entity_name="Apple",
        fiscal_year=2025,
        form="10-K",
        accession_number="test",
        source_url="https://example.test/filing",
        current_price=100.0,
        pe_ratio=20.0,
        pe_percentile=0.4,
        ps_ratio=5.0,
        ps_percentile=0.4,
        intrinsic_value_per_share=110.0,
        margin_of_safety=0.1,
        growth_rate_used=0.03,
        fcf_is_net_income_proxy=False,
        score=0.6,
        flags=["original valuation"],
    )
    experiment = Experiment(
        experiment_id=experiment_id,
        created_at=created_at,
        symbol="AAPL",
        strategy_names=["sma"],
        gate_config=config,
        trials=[trial],
        lifetime_trials=1,
        best_strategy_name="sma",
        selected_trial_index=0,
        best_gate_result=gate_result,
        fundamentals=fundamentals,
        fundamental_screen=fundamental_screen,
        distress_screen=distress_screen,
        undervaluation_score=valuation,
        graduate=graduate,
        manifest=manifest,
        data_quality_report=report,
    )
    return (
        experiment,
        trial,
        gate_result,
        graduate,
        report,
        fundamental_screen,
        distress_screen,
        valuation,
    )


def test_experiment_claim_graph_is_defensive_immutable_and_round_trips() -> None:
    experiment, trial, gate, graduate, report, fundamental, distress, valuation = _claim()
    before = experiment.model_dump(mode="json")

    trial.parameters["fast"] = 999
    gate.reasons.append("caller mutation")
    graduate.parameters["slow"] = 999
    with pytest.raises(TypeError, match="immutable"):
        report.issues[0].context["observed"] = [999.0]  # type: ignore[index]
    fundamental.reasons.append("caller mutation")
    distress.reasons.append("caller mutation")
    valuation.flags.append("caller mutation")
    assert experiment.model_dump(mode="json") == before

    with pytest.raises(AttributeError):
        experiment.strategy_names.append("momentum")
    with pytest.raises(AttributeError):
        experiment.trials.append(experiment.trials[0])
    with pytest.raises(TypeError, match="immutable"):
        experiment.trials[0].parameters["fast"] = 999
    assert experiment.best_gate_result is not None
    with pytest.raises(AttributeError):
        experiment.best_gate_result.reasons.append("public mutation")
    assert experiment.graduate is not None
    with pytest.raises(TypeError, match="immutable"):
        experiment.graduate.parameters["slow"] = 999
    assert experiment.fundamental_screen is not None
    with pytest.raises(AttributeError):
        experiment.fundamental_screen.reasons.append("public mutation")
    assert experiment.distress_screen is not None
    with pytest.raises(AttributeError):
        experiment.distress_screen.reasons.append("public mutation")
    assert experiment.undervaluation_score is not None
    with pytest.raises(AttributeError):
        experiment.undervaluation_score.flags.append("public mutation")
    assert experiment.data_quality_report is not None
    context = experiment.data_quality_report.issues[0].context
    assert context is not None
    with pytest.raises(TypeError, match="immutable"):
        context["observed"] = [999.0]
    with pytest.raises(AttributeError):
        context["observed"].append(999.0)  # type: ignore[union-attr]

    restored = Experiment.model_validate_json(experiment.model_dump_json())
    assert restored == experiment
    assert restored.model_dump(mode="json") == before


def test_experiment_rejects_selected_graduate_and_manifest_identity_drift() -> None:
    experiment, *_ = _claim()
    original = experiment.model_dump(mode="json")

    payload = deepcopy(original)
    payload["strategy_names"] = ["momentum"]
    with pytest.raises(ValidationError, match="strategy_names must exactly match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["selected_trial_index"] = 1
    with pytest.raises(ValidationError, match="selected trial index"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["parameters"]["fast"] = 10
    with pytest.raises(ValidationError, match="graduate parameters must match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["gate_result"]["holdout_sharpe"] = 2.0
    with pytest.raises(ValidationError, match="graduate gate result must match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["manifest"]["parameter_hash"] = "drift"
    with pytest.raises(ValidationError, match="manifest parameter hash must match"):
        Experiment.model_validate(payload)


def test_experiment_rejects_business_evidence_drift_and_preserves_legacy_selection() -> None:
    experiment, *_ = _claim()
    original = experiment.model_dump(mode="json")

    for field in ("fundamentals", "undervaluation_score"):
        payload = deepcopy(original)
        payload[field]["symbol"] = "MSFT"
        with pytest.raises(ValidationError, match=f"{field} symbol must match"):
            Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["fundamental_screen"]["passed"] = False
    with pytest.raises(ValidationError, match="failed fundamental screen"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["distress_screen"]["distressed"] = True
    with pytest.raises(ValidationError, match="distressed symbol"):
        Experiment.model_validate(payload)

    legacy = deepcopy(original)
    legacy["selected_trial_index"] = None
    assert selected_trial(Experiment.model_validate(legacy)).strategy_name == "sma"


def test_experiment_rejects_every_graduate_relationship_drift() -> None:
    experiment, *_ = _claim()
    original = experiment.model_dump(mode="json")

    payload = deepcopy(original)
    payload["best_strategy_name"] = "momentum"
    with pytest.raises(ValidationError, match="inconsistent with persisted best strategy"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["best_gate_result"] = None
    with pytest.raises(ValidationError, match="graduate requires the best gate"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["strategy_name"] = "momentum"
    with pytest.raises(ValidationError, match="graduate strategy must match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["best_gate_result"]["passed"] = False
    payload["graduate"]["gate_result"]["passed"] = False
    with pytest.raises(ValidationError, match="graduate requires a passing"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["holdout_sharpe"] = 2.0
    with pytest.raises(ValidationError, match="graduate holdout Sharpe must match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["graduate"]["holdout_n_bars"] = 101
    with pytest.raises(ValidationError, match="graduate holdout length must match"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["strategy_names"] = []
    payload["trials"] = []
    payload["best_strategy_name"] = None
    payload["selected_trial_index"] = None
    with pytest.raises(ValidationError, match="graduate requires the selected"):
        Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["strategy_names"] = []
    payload["trials"] = []
    payload["graduate"] = None
    payload["best_gate_result"] = None
    with pytest.raises(ValidationError, match="selected strategy requires"):
        Experiment.model_validate(payload)


def test_experiment_rejects_every_manifest_identity_drift() -> None:
    experiment, *_ = _claim()
    original = experiment.model_dump(mode="json")

    mutations = (
        ("experiment_id", str(uuid4()), "manifest experiment_id must match"),
        ("created_at", "2026-09-27T00:00:00Z", "manifest created_at must match"),
        ("strategy_name", "momentum", "manifest strategy must match"),
        ("validation_config_hash", "drift", "manifest validation config must match"),
    )
    for field, value, message in mutations:
        payload = deepcopy(original)
        payload["manifest"][field] = value
        with pytest.raises(ValidationError, match=message):
            Experiment.model_validate(payload)

    payload = deepcopy(original)
    payload["strategy_names"] = []
    payload["trials"] = []
    payload["best_strategy_name"] = None
    payload["selected_trial_index"] = None
    payload["best_gate_result"] = None
    payload["graduate"] = None
    with pytest.raises(ValidationError, match="manifest requires the selected"):
        Experiment.model_validate(payload)
