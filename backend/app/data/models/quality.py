from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.data.models.types import Severity


class DataQualityIssue(BaseModel):
    """One potential problem flagged by the DataQualityEngine (ADR-006).

    Notes:
        message wording is honest by rule (CLAUDE.md rule 6): "flags potential X", never
        "prevents/guarantees X". A check informs review; it does not certify correctness.
    """

    model_config = ConfigDict(frozen=True)

    check: str
    severity: Severity
    message: str
    context: dict[str, object] | None = None


class DataQualityReport(BaseModel):
    """Result of running the quality gate over one symbol's series (ADR-006).

    Notes:
        passed is computed, not stored as a free field, so it can never disagree with the
        issues: it is True iff no issue has severity "error". Downstream components MUST
        verify passed is True before using the data.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    checked_at: datetime
    issues: list[DataQualityIssue] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @field_validator("checked_at")
    @classmethod
    def _coerce_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware UTC; naive datetime rejected")
        return v.astimezone(UTC)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)
