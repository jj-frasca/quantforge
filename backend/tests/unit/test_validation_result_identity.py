"""ADR-159: validation result graphs are immutable, finite, coherent, and revalidated."""

from datetime import UTC, datetime

import pandas as pd
import pytest
from pydantic import ValidationError

from app.api.v1 import validation as validation_api
from app.research.lab.gate import GateConfig, GraduationGate
from app.research.lab.holdout import HoldoutScore
from app.validation.purged_cv import PurgedCVFoldResult, PurgedCVResult
from app.validation.report import Interpretation, RegimeBreakdownEntry, ValidationReport
from app.validation.walk_forward import WalkForwardResult, WalkForwardSplitResult


def _walk_forward() -> WalkForwardResult:
    return WalkForwardResult(
        n_splits=1,
        splits=[
            WalkForwardSplitResult(
                selected_config=0,
                is_sharpe=1.0,
                oos_sharpe=0.5,
                n_train=10,
                n_test=5,
            )
        ],
        mean_is_sharpe=1.0,
        mean_oos_sharpe=0.5,
        consistency=1.0,
        efficiency=0.5,
        mean_oos_hold_sharpe=0.2,
    )


def _purged_cv() -> PurgedCVResult:
    return PurgedCVResult(
        n_folds=1,
        embargo=2,
        folds=[
            PurgedCVFoldResult(
                selected_config=0,
                oos_sharpe=0.4,
                n_train=10,
                n_test=5,
            )
        ],
        mean_oos_sharpe=0.4,
        oos_sharpe_std=0.0,
        consistency=1.0,
        mean_oos_hold_sharpe=0.1,
    )


def _report() -> ValidationReport:
    return ValidationReport(
        strategy_name="sma",
        observed_sharpe=1.2,
        deflated_sharpe=0.4,
        pbo=0.2,
        parameter_stability_score=0.8,
        n_walk_forward_splits=1,
        n_purged_folds=1,
        walk_forward=_walk_forward(),
        purged_cv=_purged_cv(),
        flags=["measured"],
        interpretations=[Interpretation(metric="pbo", message="low", verdict="good")],
        regime_breakdown={"bull": RegimeBreakdownEntry(n_bars=15, total_return=0.1, sharpe=1.0)},
    )


def test_validation_result_graph_rejects_public_nested_mutation() -> None:
    report = _report()

    with pytest.raises((AttributeError, TypeError)):
        report.flags.append("changed")
    with pytest.raises((AttributeError, TypeError)):
        report.interpretations.clear()
    with pytest.raises((AttributeError, TypeError)):
        report.regime_breakdown["bear"] = report.regime_breakdown["bull"]
    assert report.walk_forward is not None
    with pytest.raises((AttributeError, TypeError)):
        report.walk_forward.splits.clear()
    assert report.purged_cv is not None
    with pytest.raises((AttributeError, TypeError)):
        report.purged_cv.folds.pop()


def test_validation_report_defensively_copies_caller_owned_containers() -> None:
    flags = ["measured"]
    interpretations = [Interpretation(metric="pbo", message="low", verdict="good")]
    regimes = {"bull": RegimeBreakdownEntry(n_bars=15, total_return=0.1, sharpe=1.0)}
    payload = _report().model_dump(round_trip=True)
    payload.update(
        {"flags": flags, "interpretations": interpretations, "regime_breakdown": regimes}
    )
    report = ValidationReport.model_validate(payload)

    flags.append("changed")
    interpretations.clear()
    regimes.clear()

    assert report.flags == ["measured"]
    assert len(report.interpretations) == 1
    assert list(report.regime_breakdown) == ["bull"]
    assert isinstance(report.model_dump()["flags"], list)
    assert isinstance(report.model_dump()["regime_breakdown"], dict)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observed_sharpe", float("nan")),
        ("deflated_sharpe", float("inf")),
        ("pbo", float("nan")),
        ("parameter_stability_score", float("nan")),
    ],
)
def test_validation_report_rejects_non_finite_headlines(field: str, value: float) -> None:
    payload = _report().model_dump(round_trip=True)
    payload[field] = value
    with pytest.raises(ValidationError, match=field):
        ValidationReport.model_validate(payload)


def test_walk_forward_result_rejects_incoherent_nested_evidence() -> None:
    payload = _walk_forward().model_dump(round_trip=True)
    payload.update(
        {
            "n_splits": 2,
            "mean_oos_sharpe": float("inf"),
            "consistency": 0.0,
        }
    )
    with pytest.raises(ValidationError):
        WalkForwardResult.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mean_is_sharpe", 0.9),
        ("mean_oos_sharpe", 0.4),
        ("consistency", 0.0),
        ("efficiency", 0.4),
    ],
)
def test_walk_forward_result_rejects_finite_summary_drift(field: str, value: float) -> None:
    payload = _walk_forward().model_dump(round_trip=True)
    payload[field] = value
    with pytest.raises(ValidationError, match=field):
        WalkForwardResult.model_validate(payload)


def test_walk_forward_result_rejects_non_finite_split_evidence() -> None:
    payload = _walk_forward().model_dump(round_trip=True)
    payload["splits"][0]["oos_sharpe"] = float("nan")
    with pytest.raises(ValidationError, match="oos_sharpe"):
        WalkForwardResult.model_validate(payload)


def test_purged_cv_result_rejects_incoherent_nested_evidence() -> None:
    payload = _purged_cv().model_dump(round_trip=True)
    payload.update({"n_folds": 2, "oos_sharpe_std": float("nan"), "consistency": 0.0})
    with pytest.raises(ValidationError):
        PurgedCVResult.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mean_oos_sharpe", 0.3),
        ("oos_sharpe_std", 0.1),
        ("consistency", 0.0),
    ],
)
def test_purged_cv_result_rejects_finite_summary_drift(field: str, value: float) -> None:
    payload = _purged_cv().model_dump(round_trip=True)
    payload[field] = value
    with pytest.raises(ValidationError, match=field):
        PurgedCVResult.model_validate(payload)


def test_purged_cv_result_rejects_non_finite_fold_evidence() -> None:
    payload = _purged_cv().model_dump(round_trip=True)
    payload["folds"][0]["oos_sharpe"] = float("inf")
    with pytest.raises(ValidationError, match="oos_sharpe"):
        PurgedCVResult.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("n_walk_forward_splits", 2), ("n_purged_folds", 2)],
)
def test_validation_report_binds_top_level_diagnostic_counts(field: str, value: int) -> None:
    payload = _report().model_dump(round_trip=True)
    payload[field] = value
    with pytest.raises(ValidationError, match=field):
        ValidationReport.model_validate(payload)


def test_gate_revalidates_an_unchecked_report_copy() -> None:
    unchecked = _report().model_copy(update={"observed_sharpe": float("nan")})
    holdout = HoldoutScore(
        sharpe=1.0,
        total_return=0.1,
        buy_and_hold_sharpe=0.0,
        n_bars=252,
    )

    with pytest.raises(ValidationError, match="observed_sharpe"):
        GraduationGate().evaluate(unchecked, 5.0, 2, holdout, GateConfig())


def test_validation_api_revalidates_an_unchecked_report_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unchecked = _report().model_copy(update={"deflated_sharpe": float("inf")})
    monkeypatch.setattr(
        validation_api,
        "_load_frame",
        lambda *args, **kwargs: pd.DataFrame({"close": range(100)}),
    )
    monkeypatch.setattr(
        validation_api.ValidationEngine,
        "validate",
        lambda *args, **kwargs: unchecked,
    )
    request = validation_api.ValidateRequest(
        symbol="AAPL",
        strategy="sma",
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2025, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ValidationError, match="deflated_sharpe"):
        validation_api.validate(request, None, None)  # type: ignore[arg-type]
