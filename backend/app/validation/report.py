from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class ValidationReport(BaseModel):
    """Aggregated validation result for one strategy — the MVP deliverable.

    Notes:
        `passed` is computed, not stored: a strategy passes only when overfitting is low
        (pbo < 0.5) AND the deflated Sharpe is still positive. The frontend renders this
        report (Phase 5). validation-methodology.md §5.
    """

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    observed_sharpe: float
    deflated_sharpe: float
    pbo: float
    n_walk_forward_splits: int
    n_purged_folds: int
    flags: list[str] = Field(default_factory=list)

    @field_validator("pbo")
    @classmethod
    def _pbo_in_unit_interval(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("pbo must be in [0, 1]")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.pbo < 0.5 and self.deflated_sharpe > 0.0
