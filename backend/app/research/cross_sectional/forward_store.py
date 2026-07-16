import json
from pathlib import Path

from app.research.cross_sectional.forward import CrossSectionalPosition


class JsonFileCrossSectionalBook:
    """Persisted cross-sectional forward book (ADR-025): frozen factor positions + their latest
    forward score and lifecycle status, JSON-backed in-repo (reviewable in git). Single-process,
    mirroring JsonFilePaperPortfolio."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def positions(self) -> list[CrossSectionalPosition]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text())
        return [CrossSectionalPosition.model_validate(item) for item in raw]

    def save(self, positions: list[CrossSectionalPosition]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump(mode="json") for p in positions]
        # Trailing newline (end-of-file-fixer), same as the other stores.
        self._path.write_text(json.dumps(payload, indent=2) + "\n")
