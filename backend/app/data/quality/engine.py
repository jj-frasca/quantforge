from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise

from app.data.models import DataQualityIssue, DataQualityReport, PriceBar


@dataclass(frozen=True)
class QualityConfig:
    """Thresholds for the heuristic checks (data-contracts.md §5). All tunable."""

    price_anomaly_pct: Decimal = Decimal("0.20")
    stale_max_repeats: int = 5
    adj_factor_low: Decimal = Decimal("0.5")
    adj_factor_high: Decimal = Decimal("2.0")
    flag_survivorship: bool = True
    min_bars: int = 2


def _business_days_between(earlier: datetime, later: datetime) -> int:
    """Count weekdays strictly between two dates (holidays not modelled — a known limit)."""
    span = (later.date() - earlier.date()).days
    return sum(1 for i in range(1, span) if (earlier.date() + timedelta(days=i)).weekday() < 5)


class DataQualityEngine:
    """Runs heuristic checks over one symbol's PriceBar series and reports findings (ADR-006).

    Notes:
        Checks FLAG potential issues; they do not guarantee correctness. Only structural
        problems that make the data unusable (insufficient data) fail the gate (error
        severity); individual anomalies are warnings that inform without blocking.
        Corporate-action and vendor cross-validation checks arrive in Phase 3 (the latter
        needs a second vendor).
    """

    def __init__(self, config: QualityConfig | None = None) -> None:
        self._config = config or QualityConfig()

    def check(self, bars: list[PriceBar], symbol: str) -> DataQualityReport:
        ordered = sorted(bars, key=lambda b: b.timestamp_utc)
        issues: list[DataQualityIssue] = []

        if len(ordered) < self._config.min_bars:
            issues.append(
                DataQualityIssue(
                    check="insufficient_data",
                    severity="error",
                    message=f"flags potential unusable series: {len(ordered)} bars (< {self._config.min_bars})",
                    context={"count": len(ordered)},
                )
            )
            return DataQualityReport(symbol=symbol, checked_at=datetime.now(UTC), issues=issues)

        if self._config.flag_survivorship:
            issues.append(
                DataQualityIssue(
                    check="survivorship_risk",
                    severity="info",
                    message=(
                        "flags potential survivorship bias: the universe may exclude delisted "
                        "symbols; not mitigated here (real mitigation needs CRSP-style data)"
                    ),
                )
            )

        issues.extend(self._missing_bars(ordered))
        issues.extend(self._price_anomaly(ordered))
        issues.extend(self._stale_data(ordered))
        issues.extend(self._split_consistency(ordered))

        return DataQualityReport(symbol=symbol, checked_at=datetime.now(UTC), issues=issues)

    def _missing_bars(self, bars: list[PriceBar]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for prev, curr in pairwise(bars):
            gap = _business_days_between(prev.timestamp_utc, curr.timestamp_utc)
            if gap > 0:
                issues.append(
                    DataQualityIssue(
                        check="missing_bars",
                        severity="warning",
                        message=f"flags potential missing bars: {gap} expected trading day(s) absent",
                        context={
                            "after": prev.timestamp_utc.isoformat(),
                            "before": curr.timestamp_utc.isoformat(),
                            "missing": gap,
                        },
                    )
                )
        return issues

    def _price_anomaly(self, bars: list[PriceBar]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        threshold = self._config.price_anomaly_pct
        for prev, curr in pairwise(bars):
            move = abs((curr.close - prev.close) / prev.close)
            if move > threshold:
                issues.append(
                    DataQualityIssue(
                        check="price_anomaly",
                        severity="warning",
                        message=f"flags potential price anomaly: {move:.2%} single-bar move (> {threshold:.0%})",
                        context={"at": curr.timestamp_utc.isoformat(), "move": str(move)},
                    )
                )
        return issues

    def _stale_data(self, bars: list[PriceBar]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        run = 1
        for prev, curr in pairwise(bars):
            if curr.close == prev.close:
                run += 1
                continue
            if run >= self._config.stale_max_repeats:
                issues.append(self._stale_issue(run))
            run = 1
        if run >= self._config.stale_max_repeats:
            issues.append(self._stale_issue(run))
        return issues

    def _stale_issue(self, run: int) -> DataQualityIssue:
        return DataQualityIssue(
            check="stale_data",
            severity="warning",
            message=f"flags potential stale data: close unchanged for {run} consecutive bars",
            context={"run": run},
        )

    def _split_consistency(self, bars: list[PriceBar]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        for prev, curr in pairwise(bars):
            ratio = curr.adj_factor / prev.adj_factor
            if ratio < self._config.adj_factor_low or ratio > self._config.adj_factor_high:
                issues.append(
                    DataQualityIssue(
                        check="split_dividend_consistency",
                        severity="warning",
                        message=f"flags potential adj_factor jump: ratio {ratio} between consecutive bars",
                        context={"at": curr.timestamp_utc.isoformat(), "ratio": str(ratio)},
                    )
                )
        return issues
