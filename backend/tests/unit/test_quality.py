"""DataQualityIssue / DataQualityReport models: severity validation, UTC checked_at, and that `passed` is computed (False iff any error-severity issue)."""

import operator
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.data.models.quality import DataQualityIssue, DataQualityReport


def _issue(severity: str = "warning", check: str = "missing_bars") -> DataQualityIssue:
    return DataQualityIssue(check=check, severity=severity, message="flags potential gap")  # type: ignore[arg-type]


def _report(**overrides: object) -> DataQualityReport:
    base: dict[str, object] = {
        "symbol": "AAPL",
        "checked_at": datetime(2024, 1, 2, tzinfo=UTC),
    }
    base.update(overrides)
    return DataQualityReport(**base)  # type: ignore[arg-type]


def test_quality_report_with_no_issues_passes() -> None:
    assert _report().passed is True


def test_quality_report_has_stable_canonical_identity() -> None:
    report = _report()

    assert isinstance(report.id, UUID)
    assert DataQualityReport.model_validate_json(report.model_dump_json()).id == report.id


def test_legacy_quality_report_without_source_is_explicitly_unknown() -> None:
    assert _report().source is None


def test_quality_report_with_warning_only_still_passes() -> None:
    assert _report(issues=[_issue("warning")]).passed is True


def test_quality_report_with_an_error_issue_fails() -> None:
    assert _report(issues=[_issue("warning"), _issue("error")]).passed is False


def test_quality_report_defensively_freezes_issue_graph_and_preserves_json_shape() -> None:
    context: dict[str, object] = {"observed": [0.25]}
    issues = [
        DataQualityIssue(
            check="price_anomaly",
            severity="warning",
            message="flags potential price anomaly",
            context=context,
        )
    ]
    report = _report(issues=issues)

    context["observed"].append(0.5)  # type: ignore[union-attr]
    issues.append(_issue("error"))
    assert len(report.issues) == 1
    assert report.issues[0].context == {"observed": [0.25]}
    assert report.passed is True

    with pytest.raises(AttributeError):
        report.issues.append(_issue("error"))  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        report.issues[0].context["observed"] = []  # type: ignore[index]
    with pytest.raises(AttributeError):
        report.issues[0].context["observed"].append(0.75)  # type: ignore[index,union-attr]

    payload = report.model_dump(mode="json")
    assert payload["issues"][0]["context"] == {"observed": [0.25]}
    assert DataQualityReport.model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize(
    "mutate",
    [
        lambda values: operator.setitem(values, 0, 3),
        lambda values: operator.delitem(values, 0),
        lambda values: operator.iadd(values, [3]),
        lambda values: operator.imul(values, 2),
        lambda values: values.append(3),
        lambda values: values.clear(),
        lambda values: values.extend([3]),
        lambda values: values.insert(0, 3),
        lambda values: values.pop(),
        lambda values: values.remove(1),
        lambda values: values.reverse(),
        lambda values: values.sort(),
    ],
)
def test_quality_issue_context_rejects_every_list_mutation(
    mutate: Callable[[list[object]], object],
) -> None:
    issue = DataQualityIssue(
        check="x",
        severity="warning",
        message="flags potential x",
        context={"values": (2, 1)},
    )
    assert issue.context is not None
    values = issue.context["values"]
    assert isinstance(values, list)

    with pytest.raises(AttributeError, match="quality report evidence is immutable"):
        mutate(values)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda context: operator.setitem(context, "new", 3),
        lambda context: operator.delitem(context, "values"),
        lambda context: operator.ior(context, {"new": 3}),
        lambda context: context.clear(),
        lambda context: context.pop("values"),
        lambda context: context.popitem(),
        lambda context: context.setdefault("new", 3),
        lambda context: context.update({"new": 3}),
    ],
)
def test_quality_issue_context_rejects_every_mapping_mutation(
    mutate: Callable[[dict[str, object]], object],
) -> None:
    issue = DataQualityIssue(
        check="x",
        severity="warning",
        message="flags potential x",
        context={"values": [2, 1]},
    )
    assert issue.context is not None

    with pytest.raises(TypeError, match="quality report evidence is immutable"):
        mutate(issue.context)


@pytest.mark.parametrize(
    "context",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": object()},
        {1: "non-string key"},
    ],
)
def test_quality_issue_rejects_non_json_context(context: object) -> None:
    with pytest.raises(ValidationError):
        DataQualityIssue(
            check="x",
            severity="warning",
            message="flags potential x",
            context=context,  # type: ignore[arg-type]
        )


def test_quality_report_symbol_is_uppercased() -> None:
    assert _report(symbol=" aapl ").symbol == "AAPL"


def test_quality_report_naive_checked_at_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _report(checked_at=datetime(2024, 1, 2))


def test_quality_report_empty_symbol_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _report(symbol="   ")


def test_quality_issue_invalid_severity_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        DataQualityIssue(check="x", severity="catastrophic", message="m")  # type: ignore[arg-type]


def test_quality_issue_message_uses_honest_wording() -> None:
    # ADR-006 / CLAUDE.md rule 6 — issues flag potential problems, not guarantees.
    issue = _issue()
    assert "flags potential" in issue.message
