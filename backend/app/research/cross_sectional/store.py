import json
from pathlib import Path
from typing import Protocol

from app.research.cross_sectional.search import CrossSectionalExperiment


class CrossSectionalExperimentStore(Protocol):
    def add(self, experiment: CrossSectionalExperiment) -> None: ...
    def all(self) -> list[CrossSectionalExperiment]: ...
    def prior_trials(self) -> int: ...


def _prior_trials(experiments: list[CrossSectionalExperiment]) -> int:
    """The cumulative cross-sectional trial count — the MinTRL denominator for the next search.
    `lifetime_trials` is cumulative when each run chains its prior from the store, so the running
    total is simply the maximum seen (0 when the pool is empty)."""
    return max((e.lifetime_trials for e in experiments), default=0)


class InMemoryCrossSectionalStore:
    """Non-persistent store for tests and single-session use."""

    def __init__(self) -> None:
        self._experiments: list[CrossSectionalExperiment] = []

    def add(self, experiment: CrossSectionalExperiment) -> None:
        self._experiments.append(experiment)

    def all(self) -> list[CrossSectionalExperiment]:
        return list(self._experiments)

    def prior_trials(self) -> int:
        return _prior_trials(self._experiments)


class JsonFileCrossSectionalStore:
    """JSON-file-backed cross-sectional pool (ADR-024), mirroring JsonFileExperimentStore. A
    per-strategy/universe record, not per-symbol. Single-process; concurrent multi-agent writes
    wait for a DB-backed impl."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def _load(self) -> list[CrossSectionalExperiment]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text())
        return [CrossSectionalExperiment.model_validate(item) for item in raw]

    def add(self, experiment: CrossSectionalExperiment) -> None:
        experiments = self._load()
        experiments.append(experiment)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [e.model_dump(mode="json") for e in experiments]
        # Trailing newline so the file satisfies the end-of-file-fixer pre-commit hook.
        self._path.write_text(json.dumps(payload, indent=2) + "\n")

    def all(self) -> list[CrossSectionalExperiment]:
        return self._load()

    def prior_trials(self) -> int:
        return _prior_trials(self._load())
