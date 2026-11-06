"""Execute ADR-417 once locally; no retries, alternative inputs or output roots.

From backend: PYTHONPATH=. uv run python scripts/published_quality_value_study.py
Never re-execute after an occupied root, failed or incomplete attempt. Verification
may replay saved bytes without any vendor call. No generated-state writer exists.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from app.data.sources.yfinance import YFinanceAdapter
from app.research.cross_sectional.published_portfolio import (
    STUDY_END,
    STUDY_START,
    evaluate_once,
    select_portfolio,
)
from app.research.dataset import current_git_revision
from app.research.fundamentals.record import FundamentalRecord

REVISION = "ca73b3047fe4a6bc6e312ce7fa94bb351215af1a"
ROOT = Path("/tmp/qf-w45-s3-adr417")
REPO = Path(__file__).resolve().parents[2]
INPUTS = {
    "data/fundamentals_pool.json": "175333955ac62b5cc4aa42822968f2aba944234dbf391af595b9197e0c644af6",
    "data/universes/sp500.txt": "ee973b82b0fba4471d6c248330929dfc0c8e4589aeb3e0cea678c1e042b38040",
}


def archived_inputs() -> tuple[list[FundamentalRecord], tuple[str, ...]]:
    """Read only the two hash-pinned Git blobs; current pools cannot supply ranks."""
    blobs = {}
    for name, digest in INPUTS.items():
        raw = subprocess.check_output(["git", "show", f"{REVISION}:{name}"], cwd=REPO)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"archive hash mismatch: {name}")
        blobs[name] = raw
    rows = [
        FundamentalRecord.model_validate(r)
        for r in json.loads(blobs["data/fundamentals_pool.json"])
    ]
    universe = tuple(
        line.strip()
        for line in blobs["data/universes/sp500.txt"].decode().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    return rows, universe


def main() -> None:
    if ROOT.exists() or ROOT.is_symlink():
        raise FileExistsError("ADR-417 attempt is frozen; never retry/resume/re-root")
    receipt_path = Path("/tmp/qf-w45-s1-fundamentals-publication.log")
    receipt = receipt_path.read_bytes()
    if b"f213059..ca73b30" not in receipt or b"2026-08-18T14:13:24.4427047Z" not in receipt:
        raise ValueError("missing successful historical publication receipt")
    records, universe = archived_inputs()
    selection = select_portfolio(records, universe)
    pool_raw = (REPO / "data/cross_sectional_pool.json").read_bytes()
    pool = json.loads(pool_raw)
    code_paths = [
        "backend/app/research/cross_sectional/published_portfolio.py",
        "backend/scripts/published_quality_value_study.py",
        "backend/tests/unit/test_published_portfolio.py",
        "docs/adr/ADR-417-evaluate-published-quality-value-portfolio.md",
    ]
    context: dict[str, object] = {
        "archive_revision": REVISION,
        "input_hashes": INPUTS,
        "publication_receipt_sha256": hashlib.sha256(receipt).hexdigest(),
        "publication_at": "2026-08-18T14:13:24.4427047Z",
        "cross_sectional_pool_sha256": hashlib.sha256(pool_raw).hexdigest(),
        "cross_sectional_experiments": len(pool),
        "represented_lifetime_max": max(r["lifetime_trials"] for r in pool),
        "executable_hashes": {
            p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in code_paths
        },
        "eligible_scores": [
            r.model_dump(mode="json") for r in records if r.symbol in selection.eligible
        ],
        "study_configs": 1,
        "searches": 0,
        "controls": 3,
        "prior_selection": "All prior hunts plus ADR414-416 including unpublished attempts; effective N unknown.",
    }
    adapter = YFinanceAdapter()  # default one adapter attempt, no CLOUD retry
    result = evaluate_once(
        ROOT,
        selection,
        lambda symbol: adapter.fetch_price_bars(symbol, STUDY_START, STUDY_END),
        adapter_version=adapter.adapter_version,
        revision=current_git_revision(),
        context=context,
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
