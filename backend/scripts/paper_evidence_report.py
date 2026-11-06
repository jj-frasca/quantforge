"""Read-only retained paper evidence (ADR-413).

Usage from backend: PYTHONPATH=. uv run python scripts/paper_evidence_report.py
Optional positional input is a historical paper-portfolio snapshot. Writes stdout
only; no vendor, broker, network, experiment or generated-state writer is called.
"""

import argparse
import hashlib
import json
from pathlib import Path

from app.research.lab.paper import PaperPosition
from app.research.lab.paper_evidence import summarize_paper_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "paper_portfolio.json",
    )
    args = parser.parse_args()
    raw = args.input.read_bytes()
    positions = [PaperPosition.model_validate(row) for row in json.loads(raw)]
    report = summarize_paper_evidence(positions)
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
