from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.validation.purged_cv import PurgedCVResult
from app.validation.result_graph import FrozenResultDict, FrozenResultList
from app.validation.walk_forward import WalkForwardResult

Verdict = Literal["good", "warning", "bad"]


class Interpretation(BaseModel):
    """Plain-English reading of one validation metric, with a verdict.

    Notes:
        Backend-authored so a non-quant reading the UI sees *what* a number means
        without knowing the methodology by heart. Verdict drives color in the frontend.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    metric: str
    message: str
    verdict: Verdict


class RegimeBreakdownEntry(BaseModel):
    """Strategy performance restricted to one market regime (bull/bear).

    Notes:
        Keys of the parent ``regime_breakdown`` dict are open-set (ADR-012) so a
        future "sideways" regime is not a breaking response change. n_bars + Sharpe
        let the frontend say "only works in bulls" when one regime carries the
        edge (validation-methodology.md §5).
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    n_bars: int = Field(ge=1)
    total_return: float = Field(allow_inf_nan=False)
    sharpe: float = Field(allow_inf_nan=False)


class ValidationReport(BaseModel):
    """Aggregated validation result for one strategy — the MVP deliverable.

    Notes:
        `passed` is computed, not stored: a strategy passes only when overfitting is low
        (pbo < 0.5) AND the deflated Sharpe is still positive. The frontend renders this
        report (Phase 5). validation-methodology.md §5.
    """

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    strategy_name: str = Field(min_length=1)
    observed_sharpe: float = Field(allow_inf_nan=False)
    deflated_sharpe: float = Field(allow_inf_nan=False)
    pbo: float = Field(allow_inf_nan=False)
    parameter_stability_score: float = Field(allow_inf_nan=False)
    n_walk_forward_splits: int = Field(ge=0)
    n_purged_folds: int = Field(ge=0)
    # ADR-038: the walk-forward splits now judge something instead of only being counted.
    # Nullable + defaulted so the experiments already in the pool deserialize unchanged, and
    # so a producer with no per-config return matrix can honestly report "not measured".
    walk_forward: WalkForwardResult | None = None
    # ADR-039: the purged folds, scored. Nullable for the same reason walk_forward is. Read it
    # NEXT TO walk_forward, never instead of it — purged CV selects using rows after its test
    # block, so it measures the edge's dispersion, not what the procedure would have earned.
    purged_cv: PurgedCVResult | None = None
    flags: list[str] = Field(default_factory=list)
    interpretations: list[Interpretation] = Field(default_factory=list)
    # ADR-012: regime breakdown for the BEST config (the one whose Sharpe drives
    # the report's headline metrics). Keyed by regime name; missing key means
    # zero bars in that regime.
    regime_breakdown: dict[str, RegimeBreakdownEntry] = Field(default_factory=dict)

    @field_validator("pbo", "parameter_stability_score")
    @classmethod
    def _in_unit_interval(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("must be in [0, 1]")
        return v

    @model_validator(mode="after")
    def _bind_and_freeze_diagnostics(self) -> "ValidationReport":
        if (
            self.walk_forward is not None
            and self.n_walk_forward_splits != self.walk_forward.n_splits
        ):
            raise ValueError("n_walk_forward_splits must agree with walk_forward")
        if self.purged_cv is not None and self.n_purged_folds != self.purged_cv.n_folds:
            raise ValueError("n_purged_folds must agree with purged_cv")
        object.__setattr__(self, "flags", FrozenResultList(list(self.flags)))
        object.__setattr__(self, "interpretations", FrozenResultList(list(self.interpretations)))
        object.__setattr__(self, "regime_breakdown", FrozenResultDict(dict(self.regime_breakdown)))
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.pbo < 0.5 and self.deflated_sharpe > 0.0


def revalidate_validation_report(report: ValidationReport) -> ValidationReport:
    """Reconstruct an untrusted report before a verdict or API publication (ADR-159)."""
    return ValidationReport.model_validate(report.model_dump(round_trip=True))
