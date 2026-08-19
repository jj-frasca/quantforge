import json
import string
from collections import defaultdict
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
    # ADR-038: mean out-of-sample Sharpe across the walk-forward windows — a prequential view
    # of the SELECTION procedure, independent of the locked holdout. Nullable + defaulted so the
    # experiments already in the pool deserialize, and so a producer that computed no
    # walk-forward (the cross-sectional search) reports "not measured" rather than 0.0.
    walk_forward_oos_sharpe: float | None = None
    # ADR-039: mean out-of-sample Sharpe across the PURGED folds. Kept separate from
    # walk_forward_oos_sharpe on purpose — the two answer different questions (causal
    # prequential vs leakage-controlled dispersion) and the GAP between them is diagnostic.
    purged_cv_oos_sharpe: float | None = None


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


_SAFE_PARTITION_CHARS = set(string.ascii_uppercase + string.digits + ".^_-")


def _partition_name(symbol: str) -> str:
    """Symbol -> partition filename stem. Real tickers (BRK-B, BF.B, ^GSPC) pass through unchanged;
    anything else is sanitized so a malformed symbol can never escape the pool directory."""
    return "".join(c if c in _SAFE_PARTITION_CHARS else "_" for c in symbol.upper())


def retain_recent(
    experiments: list[Experiment], keep_non_graduate_per_symbol: int
) -> list[Experiment]:
    """Bound a pool: keep ALL graduates (the valuable output, cheap) plus the most-recent
    `keep_non_graduate_per_symbol` NON-graduate experiments per symbol. Honest because the MinTRL
    denominator is the MAX cumulative `lifetime_trials` and the most-recent experiment — always
    kept — carries that max, so retention can never lower the graduation bar."""
    graduates = [e for e in experiments if e.graduate is not None]
    by_symbol: dict[str, list[Experiment]] = defaultdict(list)
    for e in experiments:
        if e.graduate is None:
            by_symbol[e.symbol].append(e)
    kept: list[Experiment] = list(graduates)
    for exps in by_symbol.values():
        kept.extend(
            sorted(exps, key=lambda e: e.created_at, reverse=True)[:keep_non_graduate_per_symbol]
        )
    return kept


class PartitionedExperimentStore:
    """The research pool, one JSON file per symbol (ADR-032). The single-file pool passed GitHub's
    100 MB push limit, and rewriting all of it per experiment made `add` O(pool). Here `add` and
    `trials_for_symbol` — the hot path of every hunt — touch exactly one symbol's partition, and
    ADR-026's round-robin shards write disjoint files, so the write race is structurally impossible
    rather than orchestrated around."""

    def __init__(self, directory: Path | str, keep_non_graduate_per_symbol: int = 5) -> None:
        self._dir = Path(directory)
        self._keep = keep_non_graduate_per_symbol

    def _partition(self, symbol: str) -> Path:
        return self._dir / f"{_partition_name(symbol)}.json"

    def _load_partition(self, path: Path) -> list[Experiment]:
        if not path.exists():
            return []
        return [Experiment.model_validate(item) for item in json.loads(path.read_text())]

    def add(self, experiment: Experiment) -> None:
        self.extend([experiment])

    def extend(self, experiments: list[Experiment]) -> None:
        """Fold a batch in, one partition write per touched symbol. Deduped by `experiment_id`, so
        re-running a shard replaces its experiments instead of duplicating the record."""
        incoming: dict[str, list[Experiment]] = defaultdict(list)
        for experiment in experiments:
            incoming[experiment.symbol].append(experiment)
        for symbol, batch in incoming.items():
            path = self._partition(symbol)
            by_id = {e.experiment_id: e for e in self._load_partition(path)}
            by_id.update({e.experiment_id: e for e in batch})
            self._dir.mkdir(parents=True, exist_ok=True)
            kept = retain_recent(list(by_id.values()), self._keep)
            payload = [e.model_dump(mode="json") for e in kept]
            # Trailing newline so the file satisfies the end-of-file-fixer pre-commit hook.
            path.write_text(json.dumps(payload, indent=2) + "\n")

    def all(self) -> list[Experiment]:
        return [
            exp for path in sorted(self._dir.glob("*.json")) for exp in self._load_partition(path)
        ]

    def trials_for_symbol(self, symbol: str) -> int:
        return _trials_for_symbol(self._load_partition(self._partition(symbol)), symbol)


def migrate_pool_to_partitions(
    source: Path, directory: Path, keep_non_graduate_per_symbol: int | None = None
) -> int:
    """One-shot ADR-032 migration: split a single-file pool into per-symbol partitions.

    Lossless by default — retention is disabled (`None`) so every experiment survives the move, and
    the source is removed only after the partitions are verified to hold exactly the same experiment
    ids. Passing a retention limit that would drop experiments makes the verification fail and leaves
    the source in place: a migration that silently loses part of the scientific record is a bug, not
    a feature. Refuses a non-empty destination so a re-run cannot duplicate the record. Returns the
    count migrated.
    """
    monolith = JsonFileExperimentStore(source)
    experiments = monolith.all()
    if not experiments:
        return 0
    keep = (
        len(experiments) if keep_non_graduate_per_symbol is None else keep_non_graduate_per_symbol
    )
    partitioned = PartitionedExperimentStore(directory, keep)
    if partitioned.all():
        raise RuntimeError(f"destination {directory} is not empty — refusing to migrate into it")
    for experiment in experiments:
        partitioned.add(experiment)
    expected = {e.experiment_id for e in experiments}
    if {e.experiment_id for e in partitioned.all()} != expected:
        raise RuntimeError(f"partitioned pool does not match {source} — source left in place")
    source.unlink()
    return len(experiments)
