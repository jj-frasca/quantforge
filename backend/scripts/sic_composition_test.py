"""Run the ADR-161 SIC-division composition test ONCE (single look; read-only analysis).

Usage: PYTHONPATH=. uv run python scripts/sic_composition_test.py

Reads data/research_pool/ and data/fundamentals_pool.json; writes data/sic_composition/result.json.
Refuses to run unless the ADR-161 section 7 gate holds (<= 5% of each cohort's matched symbols are
in the fundamentals pool without a sic_code).
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.research.lab.experiment import Experiment, PartitionedExperimentStore, selected_trial
from app.research.lab.pool_report import _matched
from app.research.lab.sic_composition import Member, run_test, sic_division

DATA = Path(__file__).resolve().parents[2] / "data"
OUT = DATA / "sic_composition" / "result.json"
COHORTS = (7400, 9247)
GATE = 0.05


def _per_symbol_excess(experiments: list[Experiment], bars: int) -> dict[str, float]:
    by_symbol: dict[str, list[float]] = defaultdict(list)
    for e in _matched(experiments, bars):
        if e.trials is None or e.walk_forward_hold_sharpe is None:
            continue
        oos = selected_trial(e).walk_forward_oos_sharpe
        if oos is not None:
            by_symbol[e.symbol].append(oos - e.walk_forward_hold_sharpe)
    return {s: float(np.mean(v)) for s, v in by_symbol.items()}


def main() -> int:
    experiments = PartitionedExperimentStore(DATA / "research_pool").all()
    pool = {r["symbol"]: r for r in json.loads((DATA / "fundamentals_pool.json").read_text())}
    cohorts: list[list[Member]] = []
    report: dict[str, dict[str, int]] = {}
    for bars in COHORTS:
        matched = {e.symbol for e in _matched(experiments, bars)}
        excess = _per_symbol_excess(experiments, bars)
        members: list[Member] = []
        missing_code = absent = 0
        for symbol in matched:
            if symbol not in pool:
                absent += 1
                continue
            division = sic_division(pool[symbol].get("sic_code"))
            if division is None:
                missing_code += 1
            elif symbol in excess:
                members.append(Member(division, excess[symbol]))
        if missing_code > GATE * len(matched):
            print(f"{bars}: run gate not met ({missing_code}/{len(matched)} lack sic_code)")
            return 1
        report[str(bars)] = {
            "matched": len(matched),
            "absent_from_fundamentals_pool": absent,
            "pool_row_without_sic_code": missing_code,
            "used": len(members),
        }
        cohorts.append(members)
    result = run_test(cohorts[0], cohorts[1])
    result["cohorts"] = report
    result["restriction"] = "fundamentals-eligible symbols only (ADR-161 section 7)"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
