import math

from pydantic import BaseModel, ConfigDict, Field

from app.research.backtesting.manifest import compute_parameter_hash
from app.research.lab.holdout import HoldoutScore
from app.validation.report import ValidationReport


def minbtl_years(n_trials: int, annualized_sharpe: float) -> float:
    """Minimum Backtest Length in years (Bailey & López de Prado, approximation 2·ln(N)/SR²).

    Notes:
        The track record a claimed Sharpe needs to be credible *given how many strategies were
        tried*: it grows with the number of trials and collapses as the Sharpe rises. A single
        trial (N=1) carries no selection penalty (ln 1 = 0); a non-positive Sharpe can never be
        justified (∞). See ADR-015. Cite Bailey, Borwein, López de Prado, Zhu (2014).
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if annualized_sharpe <= 0.0:
        return math.inf
    return 2.0 * math.log(n_trials) / (annualized_sharpe**2)


class GateConfig(BaseModel):
    """Versioned, tunable graduation thresholds (ADR-015/016). Recorded with every experiment so
    a result is reproducible against the exact rubric that judged it, and the calibration loop
    can compare outcomes across versions."""

    model_config = ConfigDict(frozen=True)

    dsr_min: float = 0.0
    pbo_max: float = 0.5
    stability_min: float = 0.5
    holdout_sharpe_min: float = 0.0
    # A graduate must beat simply buy-and-holding the same name on the holdout (risk-adjusted),
    # or its "edge" is just poorly-captured beta on a name that went up. Diagnosis 2026-07-02.
    require_beat_buy_and_hold: bool = True
    trial_budget: int = Field(default=200, ge=1)

    @property
    def version_hash(self) -> str:
        return compute_parameter_hash(self.model_dump())


class GateResult(BaseModel):
    """Deterministic graduation verdict — serializable so the experiment store can record the
    exact judgment for the calibration loop (ADR-015/016)."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    dsr_ok: bool
    pbo_ok: bool
    stability_ok: bool
    mintrl_ok: bool
    holdout_ok: bool
    beats_buy_and_hold_ok: bool = True
    required_track_record_years: float
    gate_config_version: str
    reasons: list[str] = Field(default_factory=list)


class GraduationGate:
    """Deterministic verdict on whether a searched strategy graduates (ADR-016). The agent may
    rank and explain survivors; it cannot override this."""

    def evaluate(
        self,
        report: ValidationReport,
        track_record_years: float,
        n_trials: int,
        holdout: HoldoutScore,
        config: GateConfig,
    ) -> GateResult:
        required = minbtl_years(n_trials, report.observed_sharpe)

        dsr_ok = report.deflated_sharpe > config.dsr_min
        pbo_ok = report.pbo < config.pbo_max
        stability_ok = report.parameter_stability_score >= config.stability_min
        mintrl_ok = track_record_years >= required
        holdout_ok = holdout.sharpe > config.holdout_sharpe_min
        beats_buy_and_hold_ok = (not config.require_beat_buy_and_hold) or (
            holdout.sharpe > holdout.buy_and_hold_sharpe
        )

        reasons: list[str] = []
        if not dsr_ok:
            reasons.append(
                f"deflated Sharpe {report.deflated_sharpe:.3f} <= {config.dsr_min} "
                "(edge vanishes once selection bias is priced in)"
            )
        if not pbo_ok:
            reasons.append(
                f"PBO {report.pbo:.3f} >= {config.pbo_max} (likely overfit — high probability the "
                "in-sample best is out-of-sample below median)"
            )
        if not stability_ok:
            reasons.append(
                f"parameter stability {report.parameter_stability_score:.3f} < {config.stability_min} "
                "(edge is fragile to small parameter changes)"
            )
        if not mintrl_ok:
            reasons.append(
                f"track record {track_record_years:.1f}y < MinTRL {required:.1f}y for "
                f"{n_trials} trials at Sharpe {report.observed_sharpe:.2f} (not enough data to "
                "justify this claim given the search effort)"
            )
        if not holdout_ok:
            reasons.append(
                f"holdout Sharpe {holdout.sharpe:.3f} <= {config.holdout_sharpe_min} "
                "(did not survive the locked out-of-sample period)"
            )
        if not beats_buy_and_hold_ok:
            reasons.append(
                f"holdout Sharpe {holdout.sharpe:.3f} <= buy-and-hold Sharpe "
                f"{holdout.buy_and_hold_sharpe:.3f} (no edge over simply holding the name — "
                "the 'edge' is just beta on a name that went up)"
            )

        passed = (
            dsr_ok
            and pbo_ok
            and stability_ok
            and mintrl_ok
            and holdout_ok
            and beats_buy_and_hold_ok
        )
        return GateResult(
            passed=passed,
            dsr_ok=dsr_ok,
            pbo_ok=pbo_ok,
            stability_ok=stability_ok,
            mintrl_ok=mintrl_ok,
            holdout_ok=holdout_ok,
            beats_buy_and_hold_ok=beats_buy_and_hold_ok,
            required_track_record_years=required,
            gate_config_version=config.version_hash,
            reasons=reasons,
        )
