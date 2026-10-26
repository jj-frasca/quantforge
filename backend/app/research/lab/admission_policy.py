"""Effective optional screen rubrics, not complete universe replay (ADR-375)."""

import json

from pydantic import BaseModel, ConfigDict, field_validator

from app.research.lab.quality_filter import QualityGateConfig
from app.research.lab.value_filter import ValueGateConfig


def _snapshot_config[Config: (ValueGateConfig, QualityGateConfig)](
    value: object, config_type: type[Config]
) -> Config | None:
    """Reconstruct without silently changing the executed rubric's finite JSON values."""
    if value is None:
        return None
    raw = value.model_dump(round_trip=True) if isinstance(value, BaseModel) else value
    rebuilt = config_type.model_validate(raw)
    original = json.dumps(raw, sort_keys=True, allow_nan=False, separators=(",", ":"))
    snapshot = json.dumps(
        rebuilt.model_dump(round_trip=True), sort_keys=True, allow_nan=False, separators=(",", ":")
    )
    if original != snapshot:
        raise ValueError("admission config must preserve complete canonical JSON evidence")
    return rebuilt


class AdmissionPolicy(BaseModel):
    """Required nullable legs distinguish known inactive screens from absent unknown policy.

    Config hashes derive from these complete snapshots. Roster, score availability/cutoff and
    filtered/error outcomes are not recorded here; this cannot reconstruct a whole hunt.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always", extra="forbid")

    value_config: ValueGateConfig | None
    quality_config: QualityGateConfig | None

    @field_validator("value_config", mode="before")
    @classmethod
    def _value_snapshot(cls, value: object) -> ValueGateConfig | None:
        return _snapshot_config(value, ValueGateConfig)

    @field_validator("quality_config", mode="before")
    @classmethod
    def _quality_snapshot(cls, value: object) -> QualityGateConfig | None:
        return _snapshot_config(value, QualityGateConfig)
