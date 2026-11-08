"""Offline ADR424 conformance only: deterministic fake prices, never a vendor."""

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from app.data.models import PriceBar
from app.research.cross_sectional.prospective_portfolio import (
    ROOT,
    evaluate_synthetic,
    prepare,
)

repo = Path.cwd()
assert (repo / "docs/evidence/ADR-424").is_dir(), "Run from repository root"
assert not ROOT.exists() and not ROOT.is_symlink(), (
    "Actual attempt root must remain absent"
)
plan = prepare(repo)
cohort = plan.cohort
out = Path(tempfile.mkdtemp(prefix="qf-adr424-synthetic-"))
summary = {"synthetic": True, "alpha_evidence_improved": False, "cases": {}}
for case in (
    "flat_fail",
    "selected_rise_pass",
    "identical_rise_tie_fail",
    "late_source_failure",
):
    calls = []

    def fake(symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        calls.append(symbol)
        assert start == datetime(2026, 11, 9, tzinfo=UTC)
        assert end == datetime(2027, 2, 11, tzinfo=UTC)
        if case == "late_source_failure" and symbol == "SPY":
            raise OSError("Explicit synthetic missing benchmark")
        bars = []
        for ordinal, label in enumerate(cohort["geometry"]["session_labels"]):
            rising = (
                case == "selected_rise_pass"
                and symbol in cohort["selection"]["selected"]
            )
            price = Decimal(100 + ordinal if rising else 100)
            if (
                case == "identical_rise_tie_fail"
                and ordinal == len(cohort["geometry"]["session_labels"]) - 1
            ):
                price = Decimal(101)
            bars.append(
                PriceBar(
                    symbol=symbol,
                    timestamp_utc=datetime.fromisoformat(label).replace(tzinfo=UTC),
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=100,
                    adj_factor=Decimal(1),
                    source="yfinance",
                )
            )
        return bars

    root = out / case
    result = evaluate_synthetic(
        plan,
        root,
        provider_factory=lambda: fake,
        clock=lambda: datetime(2027, 2, 11, tzinfo=UTC),
    )
    assert result["synthetic"] is True and result["gate_status"] == "NOT MEASURED"
    assert calls == [*cohort["selection"]["eligible"], "SPY"]
    if case == "late_source_failure":
        assert result["status"] == "UNEVALUABLE"
        assert "accounts" not in result and "screen_passed" not in result
        assert len(result["source_hashes"]) == 412
    else:
        assert result["status"] == "COMPLETE"
        assert result["screen_passed"] == (case == "selected_rise_pass")
        assert result["sessions"] == 64 and len(result["source_hashes"]) == 413
        if case == "identical_rise_tie_fail":
            assert result["net_excess"]["SPY"] == 0
            assert result["net_excess"]["eligible_equalweight"] == 0
            assert result["exact_net_returns"]["top_quintile"] == "799/100100"
            assert result["exact_net_returns"]["eligible_equalweight"] == "799/100100"
            assert result["exact_net_returns"]["SPY"] == "799/100100"
    paths = sorted(root.iterdir())
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (root / "file-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    summary["cases"][case] = {
        "status": result["status"],
        "calls": len(calls),
        "source_payloads": len(list(root.glob("source-*.json"))),
        "quality_reports": len(list(root.glob("quality-*.json"))),
        "dataset_evidence": len(list(root.glob("evidence-*.json"))),
        "screen_passed": result.get("screen_passed"),
        "accounts": result.get("accounts"),
        "net_excess": result.get("net_excess"),
        "exact_net_returns": result.get("exact_net_returns"),
        "exact_net_excess": result.get("exact_net_excess"),
        "screen_basis": result.get("screen_basis"),
        "manifest_sha256": hashlib.sha256(
            (root / "file-manifest.json").read_bytes()
        ).hexdigest(),
    }
assert not ROOT.exists() and not ROOT.is_symlink()
(out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
print(
    json.dumps({"synthetic_root": str(out), "summary_path": str(out / "summary.json")})
)
