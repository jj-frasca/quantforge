"""Final-window evaluator for immutable ADR418 (implementation ADR424).

No market execution is authorized by importing or testing this module. Synthetic
injection always refuses the registered root; the production CLI has no overrides.
"""

import gzip
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, getcontext
from fractions import Fraction
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.models import PriceBar
from app.data.quality.engine import DataQualityEngine, QualityConfig
from app.data.sources.retry import RetryPolicy
from app.research.cross_sectional.published_portfolio import funded_hold
from app.research.dataset import ResearchDataset
from app.research.frames import bars_to_frame

POLICY_REVISION = "7048c785fd34fa0fc5b8357fc711929c7fe48fb9"
SEAL_REVISION = "941dee7c2443f30e4433617a3d5070e6a8a80b60"
COHORT_GZIP_SHA = "2aaf841c39d5dfaae94d56c7a7ef2a312f34cb9a80bb7e36fbcc7d2622031f97"
COHORT_SHA = "14b888b305bd233ef60ff56edd5dd14867d8ed265676908011a866cba18a9c28"
PINNED_MANIFEST_SHA = "3d2e321c6b596352bc9f44d0f47e295698ca1969799ced816fa387be6308a4b0"
ROOT = Path("/tmp/qf-adr418-prospective-20261109-20270210")
WINDOW_START = datetime(2027, 2, 11, tzinfo=UTC)
WINDOW_END = datetime(2027, 2, 12, tzinfo=UTC)
REQUEST_START = datetime(2026, 11, 9, tzinfo=UTC)
PUBLICATION_DEADLINE = datetime(2026, 11, 9, 14, 30, tzinfo=UTC)
SEAL_RECEIPTS = {
    "ci": (42227612894, "27875db9b0b6c597aa39fe660a1b154140748bf692167693b9bfec79f95376f9"),
    "hooks": (42227612864, "883b22148f12651056254c4d80b89e6fa249cfabac10f8891966a4b382fb718f"),
}
POLICY_PATHS = (
    "app/__init__.py",
    "app/data/__init__.py",
    "app/data/sources/__init__.py",
    "app/data/sources/base.py",
    "app/data/sources/yfinance.py",
    "app/data/sources/retry.py",
    "app/data/normalizers/__init__.py",
    "app/data/normalizers/ohlcv.py",
    "app/data/models/__init__.py",
    "app/data/models/price_bar.py",
    "app/data/models/quality.py",
    "app/data/models/json_value.py",
    "app/data/models/types.py",
    "app/data/models/fundamental_data.py",
    "app/data/quality/__init__.py",
    "app/data/quality/engine.py",
    "app/research/__init__.py",
    "app/research/frames.py",
    "app/research/dataset.py",
    "app/research/trial_counts.py",
    "app/research/cross_sectional/__init__.py",
    "app/research/cross_sectional/panel.py",
    "app/research/cross_sectional/engine.py",
    "app/research/cross_sectional/published_portfolio.py",
)
Provider = Callable[[str, datetime, datetime], list[PriceBar]]
Clock = Callable[[], datetime]


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_window(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("evaluation clock must be aware")
    now = now.astimezone(UTC)
    if now < WINDOW_START:
        raise ValueError("before final evaluation window")
    if now >= WINDOW_END:
        raise ValueError("EXPIRED final evaluation window")
    return now


def _publication(raw: bytes, run_id: int, revision: str) -> dict[str, Any]:
    receipt: dict[str, Any] = json.loads(raw)
    if (
        receipt.get("databaseId") != run_id
        or receipt.get("headSha") != revision
        or receipt.get("status") != "completed"
        or receipt.get("conclusion") != "success"
        or receipt.get("event") != "push"
        or datetime.fromisoformat(receipt["updatedAt"]) >= PUBLICATION_DEADLINE
    ):
        raise ValueError("publication identity or deadline mismatch")
    return receipt


def _decimal_policy() -> dict[str, Any]:
    context = getcontext()
    policy = {
        "prec": context.prec,
        "rounding": context.rounding,
        "Emin": context.Emin,
        "Emax": context.Emax,
        "capitals": context.capitals,
        "clamp": context.clamp,
        "traps": sorted(k.__name__ for k, enabled in context.traps.items() if enabled),
    }
    if policy != {
        "prec": 28,
        "rounding": "ROUND_HALF_EVEN",
        "Emin": -999999,
        "Emax": 999999,
        "capitals": 1,
        "clamp": 0,
        "traps": ["DivisionByZero", "InvalidOperation", "Overflow"],
    }:
        raise ValueError("Decimal policy must equal standard interpreter policy")
    return {
        **policy,
        "flags": sorted(k.__name__ for k, enabled in context.flags.items() if enabled),
    }


@dataclass(frozen=True)
class PreparedStudy:
    cohort_json: bytes
    identity: dict[str, Any]

    @property
    def cohort(self) -> dict[str, Any]:
        if sha(self.cohort_json) != COHORT_SHA:
            raise ValueError("cohort hash mismatch")
        result: dict[str, Any] = json.loads(self.cohort_json)
        return result


def prepare(repo: Path) -> PreparedStudy:
    """Verify sealed inputs and active source policy, without constructing a vendor."""
    decimal_policy = _decimal_policy()
    compressed = read_bytes(repo / "docs/evidence/ADR-418/cohort.json.gz")
    if sha(compressed) != COHORT_GZIP_SHA:
        raise ValueError("cohort compressed hash mismatch")
    raw = gzip.decompress(compressed)
    plan = PreparedStudy(raw, {})
    cohort = plan.cohort
    protocol = read_bytes(repo / "docs/adr/ADR-418-seal-prospective-quality-value-portfolio.md")
    if sha(protocol) != cohort["protocol_sha256"]:
        raise ValueError("protocol hash mismatch")
    publications = {}
    manifest_raw = read_bytes(repo / "docs/evidence/ADR-424/pinned-policy.json")
    if sha(manifest_raw) != PINNED_MANIFEST_SHA:
        raise ValueError("pinned policy manifest hash mismatch")
    pinned = json.loads(manifest_raw)
    if pinned["revision"] != POLICY_REVISION or set(pinned["active_policy_sha256"]) != {
        f"backend/{p}" for p in POLICY_PATHS
    }:
        raise ValueError("pinned policy inventory identity mismatch")
    for filename, expected in cohort["publication_receipts"].items():
        receipt = read_bytes(repo / "docs/evidence/ADR-418" / filename)
        if sha(receipt) != expected["sha256"]:
            raise ValueError("input publication hash mismatch")
        publications[filename] = _publication(receipt, expected["run_id"], POLICY_REVISION)
    for kind, (run_id, digest) in SEAL_RECEIPTS.items():
        filename = f"seal-publication-{kind}.json"
        receipt = read_bytes(repo / "docs/evidence/ADR-424" / filename)
        if sha(receipt) != digest:
            raise ValueError("seal publication hash mismatch")
        publications[filename] = _publication(receipt, run_id, SEAL_REVISION)
    blobs = {}
    for name, digest in cohort["input_hashes"].items():
        entry = pinned["inputs"][name]
        compressed_blob = read_bytes(repo / "docs/evidence/ADR-424" / entry["artifact"])
        if sha(compressed_blob) != entry["compressed_sha256"]:
            raise ValueError("pinned input compressed hash mismatch")
        blob = gzip.decompress(compressed_blob)
        if sha(blob) != digest or digest != entry["sha256"]:
            raise ValueError("pinned input hash mismatch")
        blobs[name] = blob
    records = json.loads(blobs["data/fundamentals_pool.json"])
    universe = [
        line.strip()
        for line in blobs["data/universes/sp500.txt"].decode().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    admitted = [r for r in records if r["symbol"] in universe]
    if (
        len(set(universe)) != len(universe)
        or len({r["symbol"] for r in admitted}) != len(admitted)
        or len({r["cik"] for r in admitted}) != len(admitted)
    ):
        raise ValueError("ambiguous pinned input identity")
    scored = [r for r in admitted if r["combined_score"] is not None]
    by_symbol = {r["symbol"]: r for r in scored}
    eligible = [symbol for symbol in universe if symbol in by_symbol]
    ranked = sorted(scored, key=lambda r: (-r["combined_score"], r["cik"], r["symbol"]))
    selected = [r["symbol"] for r in ranked[: (len(ranked) + 4) // 5]]
    if (
        universe != cohort["full_roster"]
        or eligible != cohort["selection"]["eligible"]
        or selected != cohort["selection"]["selected"]
        or [r for r in records if r["symbol"] in eligible] != cohort["eligible_original_records"]
    ):
        raise ValueError("sealed selection or complete records mismatch")
    policy_hashes = {}
    for relative in POLICY_PATHS:
        name = f"backend/{relative}"
        expected_sha = pinned["active_policy_sha256"][name]
        if sha(read_bytes(repo / name)) != expected_sha:
            raise ValueError(f"source policy hash mismatch: {name}")
        policy_hashes[name] = expected_sha
    quality = asdict(QualityConfig())
    quality = {k: str(v) if hasattr(v, "as_tuple") else v for k, v in quality.items()}
    if quality != {
        "price_anomaly_pct": "0.20",
        "stale_max_repeats": 5,
        "adj_factor_low": "0.5",
        "adj_factor_high": "2.0",
        "corporate_action_pct": "0.50",
        "flag_survivorship": True,
        "min_bars": 2,
    }:
        raise ValueError("default quality policy mismatch")
    retry = asdict(RetryPolicy())
    if retry != {"attempts": 1, "base_delay": 1.0, "max_delay": 60.0, "min_interval": 0.0}:
        raise ValueError("default retry policy mismatch")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if os.environ.get("GITHUB_SHA", revision) != revision:
        raise ValueError("environment Git identity does not match actual HEAD")
    code_paths = [
        *sorted((repo / "backend/app").rglob("*.py")),
        repo / "backend/scripts/prospective_quality_value_study.py",
        repo / "backend/tests/unit/test_prospective_portfolio.py",
        repo / "docs/adr/ADR-424-implement-sealed-prospective-portfolio-evaluator.md",
        repo / "docs/adr/ADR-425-compare-prospective-funded-returns-exactly.md",
    ]
    identities = {str(path.relative_to(repo)): sha(read_bytes(path)) for path in code_paths}
    identity = {
        "cohort_sha256": COHORT_SHA,
        "cohort_gzip_sha256": COHORT_GZIP_SHA,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": policy_hashes,
        "actual_application_sha256": identities,
        "git_revision": revision,
        "lock_sha256": sha(read_bytes(repo / "backend/uv.lock")),
        "python": sys.version,
        "platform": platform.platform(),
        "adapter_version": f"yfinance-{version('yfinance')}",
        "installed_distributions": sorted((d.metadata["Name"], d.version) for d in distributions()),
        "decimal": decimal_policy,
        "default_quality": quality,
        "default_retry": retry,
        "publication_receipts": publications,
        "dependency_qualification": "Pinned active code policy; actual dependencies, not certified equivalent to old dependencies",
    }
    return PreparedStudy(raw, identity)


def write_json(path: Path, value: object) -> str:
    """Exclusive durable receipt. Storage failures propagate, never become source outcomes."""
    raw = json.dumps(value, indent=2, allow_nan=False).encode()
    with path.open("xb") as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())
    sync_directory(path.parent)
    return sha(raw)


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def session_prices(bars: list[PriceBar], labels: list[str]) -> pd.Series:
    dates = [bar.timestamp_utc.date().isoformat() for bar in bars]
    if dates != labels:
        raise ValueError("source must cover all 64 ordered sealed sessions exactly")
    return pd.Series(
        [float(bar.close) for bar in bars], index=pd.DatetimeIndex(labels), dtype=float
    )


def exact_funded_screen(
    endpoints: dict[str, tuple[Decimal, Decimal]], selected: list[str], eligible: list[str]
) -> dict[str, Any]:
    """Compare the unchanged fixed-unit account exactly on canonical inputs (ADR425).

    Fraction is constructed from each original Decimal before division or mean.
    Native funded_hold reports remain companions, never the strict screen basis.
    """
    legs = {"top_quintile": selected, "eligible_equalweight": eligible, "SPY": ["SPY"]}
    returns = {
        name: sum(
            (Fraction(endpoints[s][1]) / Fraction(endpoints[s][0]) for s in symbols), Fraction(0)
        )
        / len(symbols)
        * Fraction(999, 1001)
        - 1
        for name, symbols in legs.items()
    }
    returns["cash"] = Fraction(0)
    contrasts = {
        name: returns["top_quintile"] - returns[name]
        for name in ("eligible_equalweight", "SPY", "cash")
    }
    try:
        projections = {name: float(value) for name, value in contrasts.items()}
        finite = all(
            math.isfinite(float(value)) for value in (*returns.values(), *contrasts.values())
        )
    except OverflowError as exc:
        raise ValueError("exact screen projections must be finite") from exc
    if not finite:
        raise ValueError("exact screen projections must be finite")
    return {
        "exact_net_returns": {name: str(value) for name, value in returns.items()},
        "exact_net_excess": {name: str(value) for name, value in contrasts.items()},
        "net_excess": projections,
        "screen_passed": all(value > 0 for value in contrasts.values()),
        "screen_basis": {
            "method": "canonical-decimal-funded-net-v1",
            "account": "mean(Fraction(original canonical exit)/Fraction(original canonical entry))*999/1001-1",
            "decision": "All three exact rational net contrasts strictly positive; no epsilon",
            "native_accounts": "Unchanged binary64 funded_hold companion reports",
            "display": "net_excess projects exact contrasts; it need not equal native account subtraction and zero projection never decides sign",
        },
    }


def evaluate_synthetic(
    prepared: PreparedStudy, root: Path, *, provider_factory: Callable[[], Provider], clock: Clock
) -> dict[str, Any]:
    """Exercise complete sealed geometry using fake sources and temporary roots only."""
    candidates = (Path(os.path.abspath(root)), root.resolve())
    protected = (Path(os.path.abspath(ROOT)), ROOT.resolve())
    if any(
        candidate == registered or registered in candidate.parents
        for candidate in candidates
        for registered in protected
    ):
        raise ValueError("synthetic API forbids the registered root, descendants and aliases")
    return _evaluate(prepared, root, provider_factory=provider_factory, clock=clock, synthetic=True)


def _evaluate(
    prepared: PreparedStudy,
    root: Path,
    *,
    provider_factory: Callable[[], Provider],
    clock: Clock,
    synthetic: bool = False,
) -> dict[str, Any]:
    started = check_window(clock())
    cohort = prepared.cohort
    if not synthetic and root != ROOT:
        raise ValueError("production root is fixed")
    root.mkdir()
    sync_directory(root.parent)
    write_json(
        root / "START.json",
        {
            "protocol": "ADR-418/424",
            "synthetic": synthetic,
            "started_at": started.isoformat(),
            "cohort": cohort,
            "identity": prepared.identity,
        },
    )
    hashes: dict[str, str] = {}
    columns = {}
    endpoints: dict[str, tuple[Decimal, Decimal]] = {}

    def terminal(status: str, **details: Any) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(
            json.dumps(
                {
                    "status": status,
                    "synthetic": synthetic,
                    "source_hashes": hashes,
                    "gate_status": "NOT MEASURED",
                    **details,
                },
                allow_nan=False,
            )
        )
        write_json(root / "result.json", result)
        return result

    def expired() -> bool:
        try:
            check_window(clock())
        except ValueError:
            return True
        return False

    if expired():
        return terminal("INCOMPLETE", reason="evaluation window ended during START")
    provider = provider_factory()
    for ordinal, symbol in enumerate([*cohort["selection"]["eligible"], "SPY"]):
        if expired():
            return terminal("INCOMPLETE", reason="evaluation window ended before next request")
        write_json(
            root / f"attempt-{ordinal:04d}.json",
            {"symbol": symbol, "start": REQUEST_START.isoformat(), "end": WINDOW_START.isoformat()},
        )
        if expired():
            return terminal("INCOMPLETE", reason="evaluation window ended during attempt marker")
        try:
            bars = provider(symbol, REQUEST_START, WINDOW_START)
        except (ValueError, OSError, KeyError) as exc:
            if expired():
                return terminal(
                    "INCOMPLETE", failed_symbol=symbol, error=f"{type(exc).__name__}: {exc}"
                )
            return terminal(
                "UNEVALUABLE", failed_symbol=symbol, error=f"{type(exc).__name__}: {exc}"
            )
        hashes[symbol] = write_json(
            root / f"source-{ordinal:04d}.json", [bar.model_dump(mode="json") for bar in bars]
        )
        report = DataQualityEngine().check(
            bars,
            symbol,
            expected_source="yfinance",
            expected_start=REQUEST_START,
            expected_end=WINDOW_START,
        )
        write_json(root / f"quality-{ordinal:04d}.json", report.model_dump(mode="json"))
        if expired():
            return terminal(
                "INCOMPLETE",
                failed_symbol=symbol,
                reason="request returned outside evaluation window",
            )
        if not report.passed:
            return terminal(
                "UNEVALUABLE", failed_symbol=symbol, error="source quality report failed"
            )
        try:
            dataset = ResearchDataset(
                frame=bars_to_frame(bars),
                quality_report=report,
                source="yfinance",
                adapter_version="synthetic"
                if synthetic
                else str(prepared.identity["adapter_version"]),
                start=REQUEST_START,
                end=WINDOW_START,
                git_commit_hash=prepared.identity["git_revision"],
            )
        except ValueError as exc:
            return terminal(
                "UNEVALUABLE", failed_symbol=symbol, error=f"{type(exc).__name__}: {exc}"
            )
        write_json(
            root / f"evidence-{ordinal:04d}.json", dataset.evidence().model_dump(mode="json")
        )
        try:
            prices = session_prices(bars, cohort["geometry"]["session_labels"])
        except ValueError as exc:
            return terminal(
                "UNEVALUABLE", failed_symbol=symbol, error=f"{type(exc).__name__}: {exc}"
            )
        columns[symbol] = prices
        endpoints[symbol] = (bars[0].close, bars[-1].close)
    if expired():
        return terminal("INCOMPLETE", reason="evaluation window ended before accounts")
    prices = pd.DataFrame(columns)
    accounts = {
        "top_quintile": funded_hold(prices[cohort["selection"]["selected"]], cost_rate=0.001),
        "eligible_equalweight": funded_hold(
            prices[cohort["selection"]["eligible"]], cost_rate=0.001
        ),
        "SPY": funded_hold(prices[["SPY"]], cost_rate=0.001),
    }
    screen = exact_funded_screen(
        endpoints, cohort["selection"]["selected"], cohort["selection"]["eligible"]
    )
    entry_turnover = 1 / 1.001
    cost_breakdown = {
        name: {
            "entry_turnover": entry_turnover,
            "exit_turnover": account.turnover - entry_turnover,
            "entry_fee": 0.001 * entry_turnover,
            "exit_fee": 0.001 * (account.turnover - entry_turnover),
        }
        for name, account in accounts.items()
    }
    if expired():
        return terminal("INCOMPLETE", reason="evaluation window ended during accounts")
    return terminal(
        "COMPLETE",
        accounts={name: asdict(account) for name, account in accounts.items()},
        cost_breakdown=cost_breakdown,
        **screen,
        cash_return=0.0,
        sessions=64,
        exposure={"after_entry": 1.0, "after_liquidation": 0.0},
        inference="Single economic screen only; no inferential alpha or financial graduation",
    )
