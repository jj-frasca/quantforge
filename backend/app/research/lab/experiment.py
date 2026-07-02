import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.research.lab.gate import GateConfig, GateResult


class Trial(BaseModel):
    """One evaluated candidate in a search (ADR-016). Stored for EVERY candidate, winner or not
    — the DSR/MinTRL penalty needs the full denominator."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    parameters: dict[str, float | int]
    observed_sharpe: float
    deflated_sharpe: float
    pbo: float
    parameter_stability_score: float


class Graduate(BaseModel):
    """A candidate that passed the graduation gate, with its locked-holdout score."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    parameters: dict[str, float | int]
    gate_result: GateResult
    holdout_sharpe: float
    holdout_total_return: float


class Experiment(BaseModel):
    """One search run — the unit of the research pool. Reproducible: a graduate is a
    (symbol, gate_config version, holdout score) tuple backed by the full trial list."""

    model_config = ConfigDict(frozen=True)

    experiment_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    symbol: str
    strategy_names: list[str]
    gate_config: GateConfig
    trials: list[Trial]
    lifetime_trials: int
    # The best candidate's verdict is always recorded — even a REJECTION, with its reasons.
    # "Honest when it fails" (ADR-014) needs the losing gate result, not just the winners.
    best_strategy_name: str | None = None
    best_gate_result: GateResult | None = None
    graduate: Graduate | None = None
    rationale: str = ""


class ExperimentStore(Protocol):
    def add(self, experiment: Experiment) -> None: ...
    def all(self) -> list[Experiment]: ...
    def trials_for_symbol(self, symbol: str) -> int: ...


def _trials_for_symbol(experiments: list[Experiment], symbol: str) -> int:
    """Lifetime candidate count for a symbol — the denominator the DSR/MinTRL penalty needs."""
    return sum(len(e.trials) for e in experiments if e.symbol == symbol)


class InMemoryExperimentStore:
    """Non-persistent store for tests and single-session use."""

    def __init__(self) -> None:
        self._experiments: list[Experiment] = []

    def add(self, experiment: Experiment) -> None:
        self._experiments.append(experiment)

    def all(self) -> list[Experiment]:
        return list(self._experiments)

    def trials_for_symbol(self, symbol: str) -> int:
        return _trials_for_symbol(self._experiments, symbol)


class JsonFileExperimentStore:
    """JSON-file-backed pool (ADR-016): structured now, a Timescale table + vector recall later.
    Single-process; concurrent multi-agent writes wait for the DB-backed impl."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def _load(self) -> list[Experiment]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text())
        return [Experiment.model_validate(item) for item in raw]

    def add(self, experiment: Experiment) -> None:
        experiments = self._load()
        experiments.append(experiment)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [e.model_dump(mode="json") for e in experiments]
        self._path.write_text(json.dumps(payload, indent=2))

    def all(self) -> list[Experiment]:
        return self._load()

    def trials_for_symbol(self, symbol: str) -> int:
        return _trials_for_symbol(self._load(), symbol)
