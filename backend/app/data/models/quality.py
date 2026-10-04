from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
)

from app.data.models.json_value import freeze_json
from app.data.models.types import Severity, Source


class DataQualityIssue(BaseModel):
    """One potential problem flagged by the DataQualityEngine (ADR-006).

    Notes:
        message wording is honest by rule (CLAUDE.md rule 6): "flags potential X", never
        "prevents/guarantees X". A check informs review; it does not certify correctness.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    check: str
    severity: Severity
    message: str
    context: dict[str, object] | None = None

    @field_validator("context")
    @classmethod
    def _freeze_context(cls, value: dict[str, object] | None) -> dict[str, object] | None:
        if value is None:
            return None
        frozen = freeze_json(value)
        assert isinstance(frozen, dict)
        return frozen


class DataQualityReport(BaseModel):
    """Result of running the quality gate over one symbol's series (ADR-006).

    Notes:
        passed is computed, not stored as a free field, so it can never disagree with the
        issues: it is True iff no issue has severity "error". Downstream components MUST
        verify passed is True before using the data.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    id: UUID = Field(default_factory=uuid4)
    symbol: str
    source: Source | None = None
    checked_at: datetime
    issues: tuple[DataQualityIssue, ...] = Field(default_factory=tuple)

    @field_serializer("issues")
    def _serialize_issues(self, issues: tuple[DataQualityIssue, ...]) -> list[DataQualityIssue]:
        return list(issues)

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
