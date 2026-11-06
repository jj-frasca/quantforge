"""Funded fixed-unit long-only accounting for published scores (ADR-417).

This standalone exploratory evaluator neither searches nor graduates strategies.
Adjusted prices describe normalized total-return units, not broker shares.
"""

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from app.data.models import PriceBar
from app.data.quality.engine import DataQualityEngine
from app.research.cross_sectional.engine import asset_returns
from app.research.dataset import ResearchDataset
from app.research.frames import bars_to_frame
from app.research.fundamentals.record import FundamentalRecord

STUDY_START = datetime(2026, 8, 19, tzinfo=UTC)
STUDY_END = datetime(2026, 11, 6, tzinfo=UTC)  # exclusive acquisition bound


@dataclass(frozen=True)
class PortfolioSelection:
    eligible: tuple[str, ...]
    selected: tuple[str, ...]


def select_portfolio(
    records: list[FundamentalRecord], universe: tuple[str, ...]
) -> PortfolioSelection:
    """Freeze ceil-top-quintile combined ranks, breaking ties by CIK then symbol."""
    if len(set(universe)) != len(universe):
        raise ValueError("duplicate universe identity")
    admitted = [
        FundamentalRecord.model_validate(r.model_dump(round_trip=True))
        for r in records
        if r.symbol in universe
    ]
    if len({r.symbol for r in admitted}) != len(admitted) or len({r.cik for r in admitted}) != len(
        admitted
    ):
        raise ValueError("ambiguous eligible symbol/CIK identity")
    scored = [r for r in admitted if r.combined_score is not None]
    if not scored:
        raise ValueError("no eligible combined scores")
    by_symbol = {r.symbol: r for r in scored}
    ranked = sorted(scored, key=lambda r: (-float(r.combined_score), r.cik, r.symbol))  # type: ignore[arg-type]
    return PortfolioSelection(
        eligible=tuple(s for s in universe if s in by_symbol),
        selected=tuple(r.symbol for r in ranked[: math.ceil(len(ranked) / 5)]),
    )


@dataclass(frozen=True)
class FundedHoldResult:
    gross_return: float
    net_return: float
    turnover: float
    fees: float
    max_drawdown: float
    equity: tuple[float, ...]


def funded_hold(prices: pd.DataFrame, *, cost_rate: float) -> FundedHoldResult:
    """Buy equal dollars once, hold drifting units, and pay funded entry/exit fees.

    The equity path prepends initial cash, includes entry fee, and appends liquidated cash
    after the final pre-sale mark. No daily rebalance or pre-entry return is included.
    """
    if isinstance(cost_rate, bool) or not math.isfinite(cost_rate) or not 0 <= cost_rate < 1:
        raise ValueError("cost_rate must be finite and in [0,1)")
    if len(prices) < 2 or not len(prices.columns):
        raise ValueError("account requires at least two dates and one name")
    asset_returns(prices)  # reuse original price/calendar validity boundary
    relatives = prices.to_numpy(dtype=float) / prices.iloc[0].to_numpy(dtype=float)
    gross_marks = relatives.mean(axis=1)
    marks = gross_marks / (1 + cost_rate)
    terminal_notional = float(marks[-1])
    equity = np.concatenate(([1.0], marks, [terminal_notional * (1 - cost_rate)]))
    if not np.isfinite(equity).all() or (equity <= 0).any():
        raise ValueError("account equity must be finite and positive")
    turnover = 1 / (1 + cost_rate) + terminal_notional
    return FundedHoldResult(
        gross_return=float(gross_marks[-1] - 1),
        net_return=float(equity[-1] - 1),
        turnover=turnover,
        fees=cost_rate * turnover,
        max_drawdown=float((equity / np.maximum.accumulate(equity) - 1).min()),
        equity=tuple(float(v) for v in equity),
    )


def expected_sessions() -> pd.DatetimeIndex:
    """ADR-417's fixed 56 NYSE session labels (not UTC close timestamps)."""
    days = pd.bdate_range("2026-08-19", "2026-11-05")
    return days[days != pd.Timestamp("2026-09-07")]


def session_closes(bars: list[PriceBar]) -> pd.Series:
    """Match canonical UTC bar dates, retaining adjusted price values without fill."""
    series = pd.Series(
        [float(b.close) for b in bars],
        index=pd.DatetimeIndex([b.timestamp_utc.date() for b in bars]),
        dtype=float,
    )
    if not series.index.equals(expected_sessions()):
        raise ValueError("source must cover all 56 fixed sessions exactly")
    return series


def _write_json(path: Path, payload: object) -> str:
    encoded = json.dumps(payload, indent=2, allow_nan=False).encode()
    with path.open("xb") as file:
        file.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def evaluate_once(
    root: Path,
    selection: PortfolioSelection,
    provider: Callable[[str], list[PriceBar]],
    *,
    adapter_version: str,
    revision: str,
    context: dict[str, object],
) -> dict[str, object]:
    """Reserve one acquisition; a failure freezes UNEVALUABLE without partial economics.

    Existing roots always refuse before provider access. Production CLI fixes the root,
    input blobs and acquisition window; this injected boundary is also synthetic-testable.
    """
    if not selection.selected or not set(selection.selected).issubset(selection.eligible):
        raise ValueError("selected names must belong to eligible universe")
    if len(set(selection.eligible)) != len(selection.eligible) or "SPY" in selection.eligible:
        raise ValueError("eligible identity must be unique and exclude benchmark")
    root.mkdir()  # exclusive, no parents/resume/retry mode
    _write_json(
        root / "start.json",
        {
            "selection": asdict(selection),
            "context": context,
            "started_at": datetime.now(UTC).isoformat(),
            "revision": revision,
            "adapter_version": adapter_version,
            "protocol": "ADR-417",
        },
    )
    columns: dict[str, pd.Series] = {}
    source_hashes: dict[str, str] = {}
    for ordinal, symbol in enumerate((*selection.eligible, "SPY")):
        _write_json(root / f"attempt-{ordinal:04d}.json", {"symbol": symbol})
        try:
            bars = provider(symbol)
            source_hashes[symbol] = _write_json(
                root / f"source-{ordinal:04d}.json", [bar.model_dump(mode="json") for bar in bars]
            )
            start = STUDY_START
            end = STUDY_END
            report = DataQualityEngine().check(
                bars,
                symbol,
                expected_source="yfinance",
                expected_start=start,
                expected_end=end,
            )
            _write_json(root / f"quality-{ordinal:04d}.json", report.model_dump(mode="json"))
            dataset = ResearchDataset(
                frame=bars_to_frame(bars),
                quality_report=report,
                source="yfinance",
                adapter_version=adapter_version,
                start=start,
                end=end,
                git_commit_hash=revision,
            )
            _write_json(
                root / f"evidence-{ordinal:04d}.json", dataset.evidence().model_dump(mode="json")
            )
            columns[symbol] = session_closes(bars)
        except (ValueError, OSError) as exc:
            result: dict[str, object] = {
                "status": "UNEVALUABLE",
                "failed_symbol": symbol,
                "error": f"{type(exc).__name__}: {exc}",
                "source_hashes": source_hashes,
                "gate_status": "NOT MEASURED",
            }
            _write_json(root / "result.json", result)
            return result
    prices = pd.DataFrame(columns)
    accounts = {
        "top_quintile": funded_hold(prices[list(selection.selected)], cost_rate=0.001),
        "eligible_equalweight": funded_hold(prices[list(selection.eligible)], cost_rate=0.001),
        "SPY": funded_hold(prices[["SPY"]], cost_rate=0.001),
    }
    top = accounts["top_quintile"].net_return
    excess = {
        name: top - value.net_return for name, value in accounts.items() if name != "top_quintile"
    }
    excess["cash"] = top
    result = {
        "status": "COMPLETE",
        "accounts": {k: asdict(v) for k, v in accounts.items()},
        "cash_return": 0.0,
        "net_excess": excess,
        "screen_passed": all(v > 0 for v in excess.values()),
        "source_hashes": source_hashes,
        "sessions": len(prices),
        "gate_status": "NOT MEASURED",
        "inference": "retrospective exploratory only",
    }
    _write_json(root / "result.json", result)
    return result
