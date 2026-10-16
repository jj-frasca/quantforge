"""ADR-294 presentation context; recorded scientific evidence remains unchanged."""

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.research.lab.calibration import NullCalibration, PowerSweep, calibration_search_version
from app.research.lab.gate import GateConfig
from app.research.lab.history import CALIBRATION_N_BARS
from app.research.lab.search import SelectBy
from app.research.strategies.catalog import STRATEGY_CATALOG

CompatibilityState = Literal["MATCHED", "DIFFERENT", "UNKNOWN"]


class CalibrationReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    search_config_version: str
    gate_config_version: str
    n_bars: int
    strategy_names: list[str]
    n_per_param: int
    refine: bool
    refine_span: float
    select_by: SelectBy


class CalibrationCompatibility(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: CompatibilityState
    search: CompatibilityState
    gate: CompatibilityState
    history: CompatibilityState
    reasons: list[str]
    reference: CalibrationReference | None


class PresentedNullCalibration(NullCalibration):
    compatibility: CalibrationCompatibility


class PresentedPowerSweep(PowerSweep):
    compatibility: CalibrationCompatibility


def current_calibration_reference() -> CalibrationReference:
    """Describe the public default without executing a search or reading outcomes."""
    config = GateConfig()
    names = sorted(entry.name for entry in STRATEGY_CATALOG)
    return CalibrationReference(
        search_config_version=calibration_search_version(
            names,
            n_per_param=3,
            config=config,
            refine=True,
            refine_span=0.25,
            select_by="observed",
        ),
        gate_config_version=config.version_hash,
        n_bars=CALIBRATION_N_BARS,
        strategy_names=names,
        n_per_param=3,
        refine=True,
        refine_span=0.25,
        select_by="observed",
    )


def available_calibration_reference() -> CalibrationReference | None:
    """A context failure must not hide otherwise readable historical evidence."""
    try:
        return current_calibration_reference()
    except Exception:
        return None


def _combined(states: Sequence[CompatibilityState]) -> CompatibilityState:
    if "DIFFERENT" in states:
        return "DIFFERENT"
    if not states or "UNKNOWN" in states:
        return "UNKNOWN"
    return "MATCHED"


def calibration_compatibility(
    raw: Mapping[str, Any],
    reference: CalibrationReference | None,
    *,
    power: bool = False,
) -> CalibrationCompatibility:
    """Compare original metadata, before model defaults can manufacture lineage.

    This qualifies attribution only; authoritative scientific models still own
    all validation of numerical evidence and malformed artifacts.
    """
    if reference is None:
        return CalibrationCompatibility(
            status="UNKNOWN",
            search="UNKNOWN",
            gate="UNKNOWN",
            history="UNKNOWN",
            reasons=["Current default reference unavailable."],
            reference=None,
        )
    dimensions: dict[str, list[CompatibilityState]] = {k: [] for k in ["search", "gate", "history"]}
    reasons: list[str] = []

    def record(dimension: str, state: CompatibilityState, location: str, reason: str) -> None:
        dimensions[dimension].append(state)
        if state != "MATCHED":
            reasons.append(f"{location}: {reason}")

    def identity(item: Mapping[str, Any], location: str) -> None:
        for dimension, expected in [
            ("search", reference.search_config_version),
            ("gate", reference.gate_config_version),
        ]:
            value = item.get(f"{dimension}_config_version")
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
                record(
                    dimension, "UNKNOWN", location, f"Recorded {dimension} identity unavailable."
                )
            elif value != expected:
                record(
                    dimension,
                    "DIFFERENT",
                    location,
                    f"Recorded {dimension} identity differs from current default.",
                )
            else:
                record(dimension, "MATCHED", location, "")

    def history(item: Mapping[str, Any], location: str, *, header: bool = False) -> None:
        value = item.get("n_bars")
        if header:
            values = [value]
            complete = type(value) is int and value > 0
        else:
            values = value if isinstance(value, list) else []
            count = item.get("n_symbols")
            complete = (
                type(count) is int
                and count > 0
                and len(values) == count
                and all(type(v) is int and v > 0 for v in values)
            )
        if any(type(v) is int and v > 0 and v != reference.n_bars for v in values):
            record(
                "history", "DIFFERENT", location, "Recorded history differs from current target."
            )
            if not complete:
                reasons.append(f"{location}: Recorded history is also incomplete or unavailable.")
        elif not complete:
            record("history", "UNKNOWN", location, "Complete recorded history unavailable.")
        else:
            record("history", "MATCHED", location, "")

    identity(raw, "Sweep" if power else "Null calibration")
    history(raw, "Sweep" if power else "Null calibration", header=power)
    if power:
        cells = raw.get("cells")
        if not isinstance(cells, list) or not cells:
            for dimension in dimensions:
                record(dimension, "UNKNOWN", "Sweep", "Cell evidence unavailable.")
        else:
            for i, cell in enumerate(cells):
                item = cell if isinstance(cell, Mapping) else {}
                identity(item, f"Cell {i + 1}")
                history(item, f"Cell {i + 1}")
    search, gate, hist = [_combined(dimensions[k]) for k in ["search", "gate", "history"]]
    return CalibrationCompatibility(
        status=_combined([search, gate, hist]),
        search=search,
        gate=gate,
        history=hist,
        reasons=reasons,
        reference=reference,
    )
