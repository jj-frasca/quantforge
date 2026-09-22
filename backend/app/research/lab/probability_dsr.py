"""Pre-registered probability-form DSR gate comparison (ADR-102).

This module deliberately reads only complete future calibration artifacts. It never chooses a
threshold from their values: ADR-102 fixed the strict probability > 0.95 rule and the decision
criterion before any qualifying null or power record existed.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import binomtest

from app.research.lab.calibration import (
    PROBABILITY_DSR_THRESHOLD,
    CalibrationSymbolVerdict,
    NullCalibration,
    PowerCalibration,
    PowerSweep,
)
from app.research.lab.universe import expected_max_sharpe_under_null

_TRADING_DAYS = 252
_REQUIRED_NULL_MODES = {"iid_normal", "bootstrap:SPY"}
_STRONG_EDGE_PHIS = (-0.30, 0.30)
_MIN_NULL_SYMBOLS = 200
_MIN_POWER_SYMBOLS = 50


class ProbabilityDsrCellComparison(BaseModel):
    """One pre-registered strong-edge cell under incumbent and candidate DSR rules."""

    model_config = ConfigDict(frozen=True)

    phi: float
    n_symbols: int = Field(ge=_MIN_POWER_SYMBOLS)
    incumbent_detections: int
    candidate_detections: int
    incumbent_survivors: int
    candidate_survivors: int
    candidate_only: int
    incumbent_only: int


class ProbabilityDsrGateComparison(BaseModel):
    """The complete ADR-102 decision record; `passed` authorizes only a later gate-change ADR."""

    model_config = ConfigDict(frozen=True)

    threshold: float
    null_candidate_graduates: dict[str, int]
    null_candidate_survivors: dict[str, int]
    strong_edge_cells: list[ProbabilityDsrCellComparison]
    candidate_only: int
    incumbent_only: int
    mcnemar_pvalue: float
    passed: bool


def _joint_verdicts(
    verdicts: Sequence[CalibrationSymbolVerdict],
    expected_n: int,
    label: str,
    gate_config_version: str,
) -> list[CalibrationSymbolVerdict]:
    if len(verdicts) != expected_n:
        raise ValueError(f"{label} has no complete joint verdict for every searched symbol")
    if any(verdict.passes_preregistered_probability_gate is None for verdict in verdicts):
        raise ValueError(f"{label} has an unmeasured probability in its joint verdict")
    if any(verdict.gate_result.gate_config_version != gate_config_version for verdict in verdicts):
        raise ValueError(f"{label} has an embedded gate_config_version mismatch")
    return list(verdicts)


def _candidate_passes(verdict: CalibrationSymbolVerdict) -> bool:
    passed = verdict.passes_preregistered_probability_gate
    if passed is None:  # guarded by `_joint_verdicts`; retained as a type-narrowing invariant.
        raise ValueError("joint verdict has no probability measurement")
    return passed


def _survives(verdict: CalibrationSymbolVerdict, *, n_symbols: int, candidate: bool) -> bool:
    passes = _candidate_passes(verdict) if candidate else verdict.gate_result.passed
    if not passes:
        return False
    bar = expected_max_sharpe_under_null(n_symbols, verdict.holdout_n_bars / _TRADING_DAYS)
    return verdict.holdout_sharpe > bar


def _validate_identity(nulls: Sequence[NullCalibration], power: PowerSweep) -> None:
    modes = {calibration.null_mode for calibration in nulls}
    if modes != _REQUIRED_NULL_MODES or len(nulls) != len(_REQUIRED_NULL_MODES):
        raise ValueError("need exactly iid_normal and bootstrap:SPY null calibrations for ADR-102")
    gate_versions = {calibration.gate_config_version for calibration in nulls}
    gate_versions.add(power.gate_config_version)
    if len(gate_versions) != 1:
        raise ValueError("gate_config_version differs across probability-DSR evidence")
    search_versions = {calibration.search_config_version for calibration in nulls}
    search_versions.add(power.search_config_version)
    if len(search_versions) != 1:
        raise ValueError("search_config_version differs across probability-DSR evidence")
    for calibration in nulls:
        if set(calibration.n_bars) != {power.n_bars}:
            raise ValueError("n_bars differs across probability-DSR evidence")
    for cell in power.cells:
        if cell.edge != power.edge:
            raise ValueError("power cell edge differs from its sweep")
        if cell.gate_config_version != power.gate_config_version:
            raise ValueError("power cell gate_config_version differs from its sweep")
        if cell.search_config_version != power.search_config_version:
            raise ValueError("power cell search_config_version differs from its sweep")
        if len(cell.n_bars) != cell.n_symbols or set(cell.n_bars) != {power.n_bars}:
            raise ValueError("power cell n_bars differs from its sweep")


def _compare_cell(cell: PowerCalibration) -> ProbabilityDsrCellComparison:
    if cell.phi not in _STRONG_EDGE_PHIS:
        raise ValueError(f"phi={cell.phi} is not an ADR-102 strong-edge cell")
    if cell.n_symbols < _MIN_POWER_SYMBOLS:
        raise ValueError(f"phi={cell.phi} needs at least {_MIN_POWER_SYMBOLS} symbols")
    verdicts = _joint_verdicts(
        cell.symbol_verdicts,
        cell.n_symbols,
        f"phi={cell.phi}",
        cell.gate_config_version,
    )
    incumbent = [verdict.gate_result.passed for verdict in verdicts]
    candidate = [_candidate_passes(verdict) for verdict in verdicts]
    return ProbabilityDsrCellComparison(
        phi=cell.phi,
        n_symbols=cell.n_symbols,
        incumbent_detections=sum(incumbent),
        candidate_detections=sum(candidate),
        incumbent_survivors=sum(
            _survives(verdict, n_symbols=cell.n_symbols, candidate=False) for verdict in verdicts
        ),
        candidate_survivors=sum(
            _survives(verdict, n_symbols=cell.n_symbols, candidate=True) for verdict in verdicts
        ),
        candidate_only=sum(new and not old for old, new in zip(incumbent, candidate, strict=True)),
        incumbent_only=sum(old and not new for old, new in zip(incumbent, candidate, strict=True)),
    )


def compare_probability_dsr_gate(
    nulls: Sequence[NullCalibration], power: PowerSweep
) -> ProbabilityDsrGateComparison:
    """Apply ADR-102's fixed threshold, sample floors, pairing test, and acceptance criterion."""
    _validate_identity(nulls, power)

    null_graduates: dict[str, int] = {}
    null_survivors: dict[str, int] = {}
    for calibration in sorted(nulls, key=lambda item: item.null_mode):
        if calibration.n_symbols < _MIN_NULL_SYMBOLS:
            raise ValueError(f"{calibration.null_mode} needs at least {_MIN_NULL_SYMBOLS} symbols")
        verdicts = _joint_verdicts(
            [
                diagnostic.calibration_verdict
                for diagnostic in calibration.symbol_diagnostics
                if diagnostic.calibration_verdict is not None
            ],
            calibration.n_symbols,
            calibration.null_mode,
            calibration.gate_config_version,
        )
        null_graduates[calibration.null_mode] = sum(_candidate_passes(v) for v in verdicts)
        null_survivors[calibration.null_mode] = sum(
            _survives(v, n_symbols=calibration.n_symbols, candidate=True) for v in verdicts
        )

    if power.edge != "ar1":
        raise ValueError("ADR-102 requires the AR(1) power sweep")
    strong_cells = [cell for cell in power.cells if cell.phi in _STRONG_EDGE_PHIS]
    if len({cell.phi for cell in strong_cells}) != len(strong_cells):
        raise ValueError("power sweep contains a duplicate ADR-102 strong-edge cell")
    cells_by_phi = {cell.phi: cell for cell in strong_cells}
    if any(phi not in cells_by_phi for phi in _STRONG_EDGE_PHIS):
        raise ValueError("power sweep is missing an ADR-102 strong-edge cell")
    comparisons = [_compare_cell(cells_by_phi[phi]) for phi in _STRONG_EDGE_PHIS]

    candidate_only = sum(cell.candidate_only for cell in comparisons)
    incumbent_only = sum(cell.incumbent_only for cell in comparisons)
    discordant = candidate_only + incumbent_only
    pvalue = (
        float(binomtest(candidate_only, discordant, 0.5, alternative="greater").pvalue)
        if discordant
        else 1.0
    )
    no_type_i_regression = not any(null_graduates.values()) and not any(null_survivors.values())
    no_strong_edge_regression = all(
        cell.candidate_detections >= cell.incumbent_detections
        and cell.candidate_survivors >= cell.incumbent_survivors
        for cell in comparisons
    )
    evidence_of_benefit = candidate_only > incumbent_only and pvalue < 0.05

    return ProbabilityDsrGateComparison(
        threshold=PROBABILITY_DSR_THRESHOLD,
        null_candidate_graduates=null_graduates,
        null_candidate_survivors=null_survivors,
        strong_edge_cells=comparisons,
        candidate_only=candidate_only,
        incumbent_only=incumbent_only,
        mcnemar_pvalue=pvalue,
        passed=no_type_i_regression and no_strong_edge_regression and evidence_of_benefit,
    )
