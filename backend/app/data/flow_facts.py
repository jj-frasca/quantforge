"""Selected flow-row attribution only; no annual-period or PIT certification (ADR-419)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data.models.json_value import freeze_json


class SelectedFlowFact(BaseModel):
    model_config = ConfigDict(
        frozen=True, revalidate_instances="always", extra="forbid", strict=True
    )

    tag: str
    unit: str
    row: dict[str, object]

    @field_validator("row")
    @classmethod
    def freeze_row(cls, value: dict[str, object]) -> dict[str, object]:
        frozen = freeze_json(value)
        assert isinstance(frozen, dict)
        return frozen


class SelectedFlowFacts(BaseModel):
    model_config = ConfigDict(
        frozen=True, revalidate_instances="always", extra="forbid", strict=True
    )

    revenue: SelectedFlowFact | None = Field(default=None, exclude_if=lambda v: v is None)
    net_income: SelectedFlowFact | None = Field(default=None, exclude_if=lambda v: v is None)
    eps: SelectedFlowFact | None = Field(default=None, exclude_if=lambda v: v is None)


class AnnualFlowFacts(BaseModel):
    model_config = ConfigDict(
        frozen=True, revalidate_instances="always", extra="forbid", strict=True
    )

    fiscal_year: int
    facts: SelectedFlowFacts | None = None  # explicit unknown year in a partially known history
