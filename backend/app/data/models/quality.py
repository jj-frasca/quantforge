import math
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Never, SupportsIndex
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
)

from app.data.models.types import Severity, Source


class _FrozenJsonList(list[object]):
    @staticmethod
    def _immutable() -> Never:
        raise AttributeError("quality report evidence is immutable")

    def __setitem__(self, key: object, value: object) -> Never:
        self._immutable()

    def __delitem__(self, key: object) -> Never:
        self._immutable()

    def __iadd__(self, value: object) -> Never:  # type: ignore[misc]
        self._immutable()

    def __imul__(self, value: object) -> Never:
        self._immutable()

    def append(self, value: object) -> Never:
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def extend(self, values: object) -> Never:
        self._immutable()

    def insert(self, index: SupportsIndex, value: object) -> Never:
        self._immutable()

    def pop(self, index: SupportsIndex = -1) -> Never:
        self._immutable()

    def remove(self, value: object) -> Never:
        self._immutable()

    def reverse(self) -> Never:
        self._immutable()

    def sort(self, *args: object, **kwargs: object) -> Never:
        self._immutable()


class _FrozenJsonDict(dict[str, object]):
    @staticmethod
    def _immutable() -> Never:
        raise TypeError("quality report evidence is immutable")

    def __setitem__(self, key: str, value: object) -> Never:
        self._immutable()

    def __delitem__(self, key: str) -> Never:
        self._immutable()

    def __ior__(self, other: object) -> Never:  # type: ignore[misc]
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def pop(self, key: str, default: object = None) -> Never:
        self._immutable()

    def popitem(self) -> Never:
        self._immutable()

    def setdefault(self, key: str, default: object = None) -> Never:
        self._immutable()

    def update(self, *args: object, **kwargs: object) -> Never:
        self._immutable()


def _freeze_json(value: object) -> object:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("quality issue context floats must be finite")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("quality issue context keys must be strings")
        return _FrozenJsonDict({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return _FrozenJsonList([_freeze_json(item) for item in value])
    raise ValueError("quality issue context must contain only JSON-compatible values")


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
        frozen = _freeze_json(value)
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
