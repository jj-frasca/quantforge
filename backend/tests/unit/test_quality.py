from datetime import UTC, datetime

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


def test_quality_report_with_warning_only_still_passes() -> None:
    assert _report(issues=[_issue("warning")]).passed is True


def test_quality_report_with_an_error_issue_fails() -> None:
    assert _report(issues=[_issue("warning"), _issue("error")]).passed is False


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
