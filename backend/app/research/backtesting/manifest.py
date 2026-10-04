import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def compute_parameter_hash(params: Mapping[str, object]) -> str:
    """Deterministic, order-independent SHA256 of a parameter dict."""
    payload = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class ExperimentManifest(BaseModel):
    """Data-lineage record that makes a backtest a reproducible scientific claim.

    Notes:
        Without the full lineage (code version, parameter hash, data source + quality snapshot,
        adapter version), a backtest result is not reproducible. Round-trips JSON losslessly
        (§8 invariant #10).
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    experiment_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_commit_hash: str
    strategy_name: str
    parameter_hash: str
    data_source: str
    symbol: str
    start_date: date
    end_date: date
    data_quality_report_id: UUID | None = None
    adapter_version: str
    validation_config_hash: str | None = None
    benchmark_symbol: str = "SPY"

    @field_validator("created_at")
    @classmethod
    def _coerce_created_at_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("manifest created_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("git_commit_hash")
    @classmethod
    def _validate_git_revision(cls, value: str) -> str:
        if not _FULL_GIT_SHA.fullmatch(value):
            raise ValueError("git_commit_hash must be a 40-character lowercase hexadecimal SHA")
        return value

    @field_validator("parameter_hash", "validation_config_hash")
    @classmethod
    def _validate_hash(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256.fullmatch(value):
            raise ValueError("manifest hashes must be 64-character lowercase hexadecimal values")
        return value

    @field_validator("strategy_name", "data_source", "adapter_version")
    @classmethod
    def _require_identity(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must be non-empty")
        return value

    @field_validator("symbol", "benchmark_symbol")
    @classmethod
    def _normalize_symbol(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError(f"{info.field_name} must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _validate_range(self) -> "ExperimentManifest":
        if self.start_date >= self.end_date:
            raise ValueError("manifest start_date must be before end_date")
        return self
