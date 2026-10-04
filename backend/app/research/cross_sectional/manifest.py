"""Reproducibility identity for one multi-symbol cross-sectional claim (ADR-138)."""

import re
from datetime import UTC, date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from app.data.models import Source
from app.research.claim_graph import FrozenClaimList

_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")


class PanelComponentManifest(BaseModel):
    """Lineage for one retained column of a cross-sectional price panel."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    symbol: str
    data_source: Source
    adapter_version: str
    start_date: date
    end_date: date
    data_quality_report_id: UUID

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("panel component symbol must be non-empty")
        return normalized

    @field_validator("adapter_version")
    @classmethod
    def _require_adapter_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("panel component adapter_version must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_range(self) -> "PanelComponentManifest":
        if self.start_date >= self.end_date:
            raise ValueError("panel component start_date must be before end_date")
        return self


class CrossSectionalManifest(BaseModel):
    """Shared identity plus ordered per-symbol evidence for one panel search."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    experiment_id: UUID
    created_at: datetime
    git_commit_hash: str
    strategy_name: str
    parameter_hash: str
    validation_config_hash: str
    components: list[PanelComponentManifest]
    benchmark: str = "equal_weight_universe"

    @field_validator("strategy_name", "benchmark")
    @classmethod
    def _require_identity(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must be non-empty")
        return value

    @field_validator("created_at")
    @classmethod
    def _coerce_created_at_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("panel manifest created_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("git_commit_hash")
    @classmethod
    def _validate_git_revision(cls, value: str) -> str:
        if not _FULL_GIT_SHA.fullmatch(value):
            raise ValueError("git_commit_hash must be a 40-character lowercase hexadecimal SHA")
        return value

    @field_validator("parameter_hash", "validation_config_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("manifest hashes must be 64-character lowercase hexadecimal values")
        return value

    @model_validator(mode="after")
    def _validate_components(self) -> "CrossSectionalManifest":
        components = [
            PanelComponentManifest.model_validate(component.model_dump(round_trip=True))
            for component in self.components
        ]
        symbols = [component.symbol for component in components]
        if not symbols:
            raise ValueError("panel manifest requires at least one component")
        if len(symbols) != len(set(symbols)):
            raise ValueError("panel manifest component symbols must be unique")
        object.__setattr__(self, "components", FrozenClaimList(components))
        return self
