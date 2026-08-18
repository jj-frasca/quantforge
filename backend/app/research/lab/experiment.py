import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.data.fundamentals import FundamentalScreen, FundamentalSnapshot
from app.research.fundamentals.distress import DistressScreen
from app.research.lab.gate import GateConfig, GateResult
from app.research.valuation import UndervaluationScore


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
    holdout_n_bars: int = 0  # holdout length -> track-record years for universe deflation (ADR-018)


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
    # Fundamentals context for the symbol (ADR-017): the cited snapshot + whether it cleared the
    # 'sane fundamentals' screen. A failed screen vetoes graduation regardless of the technicals.
    fundamentals: FundamentalSnapshot | None = None
    fundamental_screen: FundamentalScreen | None = None
    # Hard financial-distress rail (ADR-029 Layer 3c): the distress screen computed at hunt time.
    # A distressed name is vetoed from graduation regardless of technicals — a business-quality
    # safety rail on top of the ADR-017 fundamentals veto. None when the sweep data was unavailable.
    distress_screen: DistressScreen | None = None
    # Cited undervaluation score at hunt time (ADR-023), recorded so we can later measure whether
    # value+algo survivors outperform. None when value is off or the name is unscorable (e.g. ETF).
    undervaluation_score: UndervaluationScore | None = None
    graduate: Graduate | None = None
    rationale: str = ""


class ExperimentStore(Protocol):
    def add(self, experiment: Experiment) -> None: ...
    def all(self) -> list[Experiment]: ...
    def trials_for_symbol(self, symbol: str) -> int: ...


def _trials_for_symbol(experiments: list[Experiment], symbol: str) -> int:
    """Lifetime candidate count for a symbol — the DSR/MinTRL penalty denominator. The MAX cumulative
    ``lifetime_trials`` across the symbol's experiments (each is prior + this run's trials, so it is
    cumulative and non-decreasing). Max, not a sum of trial-list lengths, so the count SURVIVES pool
    pruning: dropping old experiments never lowers the bar as long as the most-recent (max) one is
    kept (ADR-026 pool-size fix). Equivalent to the old sum for an un-pruned cumulative pool."""
    return max((e.lifetime_trials for e in experiments if e.symbol == symbol), default=0)


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
        # Trailing newline so the file satisfies the end-of-file-fixer pre-commit hook and doesn't
        # churn on every regeneration (which otherwise collides with pre-commit's stash).
        self._path.write_text(json.dumps(payload, indent=2) + "\n")

    def all(self) -> list[Experiment]:
        return self._load()

    def trials_for_symbol(self, symbol: str) -> int:
        return _trials_for_symbol(self._load(), symbol)
