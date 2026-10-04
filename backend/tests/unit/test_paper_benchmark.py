"""Offline inception anchoring for the paper-account daily-close benchmark."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scripts import paper_broker

from app.data.models import PriceBar
from app.data.sources.base import DataSourceAdapter
from app.execution.alpaca_broker import AlpacaAccount
from app.execution.equity_curve import EquityPoint, JsonFileEquityCurve

NY = ZoneInfo("America/New_York")


class DailyAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "offline-1"

    def __init__(self, bars: list[PriceBar]) -> None:
        self.bars = bars
        self.requests: list[tuple[str, datetime, datetime]] = []

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        self.requests.append((symbol, start, end))
        return [bar for bar in self.bars if start <= bar.timestamp_utc < end]


def daily(day: int, close: float, *, month: int = 8) -> PriceBar:
    price = Decimal(str(close))
    return PriceBar(
        symbol="SPY",
        timestamp_utc=datetime(2026, month, day, tzinfo=NY),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1000,
        adj_factor=Decimal("1"),
        source="yfinance",
    )


def test_benchmark_includes_completed_inception_close() -> None:
    adapter = DailyAdapter([daily(4, 100), daily(5, 110), daily(6, 121)])
    inception = datetime(2026, 8, 5, 2, tzinfo=UTC)  # Aug 4, 22:00 New York.
    now = datetime(2026, 8, 7, 2, tzinfo=UTC)
    result = paper_broker.fetch_benchmark_return(
        adapter,
        inception,
        now,
        git_commit_hash="a" * 40,
    )
    assert result == pytest.approx(0.21)
    symbol, start, end = adapter.requests[0]
    assert symbol == "SPY"
    assert start < adapter.bars[0].timestamp_utc < inception
    assert end == now


def measure(adapter: DailyAdapter, inception: datetime, now: datetime) -> float | None:
    return paper_broker.fetch_benchmark_return(
        adapter,
        inception,
        now,
        git_commit_hash="a" * 40,
    )


@pytest.mark.parametrize("hour, minute", [(9, 30), (12, 0), (15, 59)])
def test_benchmark_intraday_endpoint_is_unmeasured(hour: int, minute: int) -> None:
    adapter = DailyAdapter([daily(4, 100), daily(5, 110), daily(6, 121)])
    assert (
        measure(
            adapter,
            datetime(2026, 8, 4, 22, tzinfo=NY),
            datetime(2026, 8, 6, hour, minute, tzinfo=NY),
        )
        is None
    )
    assert adapter.requests == []


def test_benchmark_intraday_inception_is_unmeasured() -> None:
    adapter = DailyAdapter([daily(4, 100), daily(5, 110)])
    assert (
        measure(adapter, datetime(2026, 8, 4, 12, tzinfo=NY), datetime(2026, 8, 5, 22, tzinfo=NY))
        is None
    )
    assert adapter.requests == []


@pytest.mark.parametrize("hour", [8, 9])
def test_benchmark_preopen_excludes_forming_today_bar(hour: int) -> None:
    adapter = DailyAdapter([daily(4, 100), daily(5, 110), daily(6, 121)])
    assert measure(
        adapter, datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 6, hour, tzinfo=NY)
    ) == pytest.approx(0.10)


def test_benchmark_at_regular_close_uses_today() -> None:
    adapter = DailyAdapter([daily(4, 100), daily(5, 110)])
    assert measure(
        adapter, datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 5, 16, tzinfo=NY)
    ) == pytest.approx(0.10)


@pytest.mark.parametrize("day", [7, 8, 9, 10])
def test_benchmark_weekend_and_monday_preopen_use_friday(day: int) -> None:
    adapter = DailyAdapter([daily(6, 100), daily(7, 110)])
    assert measure(
        adapter, datetime(2026, 8, 6, 22, tzinfo=NY), datetime(2026, 8, day, 8, tzinfo=NY)
    ) == pytest.approx(0.10 if day > 7 else 0)


def test_benchmark_same_completed_session_has_zero_return() -> None:
    adapter = DailyAdapter([daily(3, 90), daily(4, 100)])
    assert (
        measure(adapter, datetime(2026, 8, 4, 20, tzinfo=NY), datetime(2026, 8, 5, 8, tzinfo=NY))
        == 0.0
    )


def test_benchmark_dst_transition_uses_new_york_session_dates() -> None:
    adapter = DailyAdapter([daily(6, 100, month=3), daily(9, 110, month=3)])
    assert measure(
        adapter, datetime(2026, 3, 7, 2, tzinfo=UTC), datetime(2026, 3, 10, 2, tzinfo=UTC)
    ) == pytest.approx(0.10)
    assert adapter.requests[0][1].astimezone(NY).hour == 0


@pytest.mark.parametrize("missing", [4, 6])
def test_benchmark_missing_exact_anchor_cannot_use_stale_bar(missing: int) -> None:
    adapter = DailyAdapter([daily(day, 100 + day) for day in [3, 4, 5, 6] if day != missing])
    assert (
        measure(adapter, datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 6, 22, tzinfo=NY))
        is None
    )


@pytest.mark.parametrize("bars", [[], [daily(4, 100)], [daily(4, 100), daily(4, 110)]])
def test_benchmark_quality_failure_is_unmeasured(bars: list[PriceBar]) -> None:
    assert (
        measure(
            DailyAdapter(bars),
            datetime(2026, 8, 4, 22, tzinfo=NY),
            datetime(2026, 8, 6, 22, tzinfo=NY),
        )
        is None
    )


def test_benchmark_noncanonical_daily_labels_are_unmeasured() -> None:
    bars = [
        daily(day, 100 + day).model_copy(
            update={
                "timestamp_utc": datetime(2026, 8, day, tzinfo=UTC),
            }
        )
        for day in [4, 5, 6]
    ]
    assert (
        measure(
            DailyAdapter(bars),
            datetime(2026, 8, 4, 22, tzinfo=NY),
            datetime(2026, 8, 6, 22, tzinfo=NY),
        )
        is None
    )


@pytest.mark.parametrize(
    "failure", [OSError("offline"), ValueError("vendor"), ArithmeticError("bad")]
)
def test_benchmark_fetch_failure_is_unmeasured(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    adapter = DailyAdapter([])

    def fail(*_args: object) -> list[PriceBar]:
        raise failure

    monkeypatch.setattr(adapter, "fetch_price_bars", fail)
    assert (
        measure(adapter, datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 6, 22, tzinfo=NY))
        is None
    )


@pytest.mark.parametrize(
    "inception,now",
    [
        (datetime(2026, 8, 4), datetime(2026, 8, 6, 22, tzinfo=NY)),
        (datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 6)),
        (datetime(2026, 8, 6, 22, tzinfo=NY), datetime(2026, 8, 4, 22, tzinfo=NY)),
    ],
)
def test_benchmark_ambiguous_or_reversed_timestamps_are_unmeasured(
    inception: datetime, now: datetime
) -> None:
    adapter = DailyAdapter([])
    assert measure(adapter, inception, now) is None
    assert adapter.requests == []


@pytest.mark.parametrize("first,last", [(1e-300, 1e300), (1e300, 1e-300)])
def test_benchmark_unrepresentable_float_return_is_unmeasured(first: float, last: float) -> None:
    adapter = DailyAdapter([daily(4, first), daily(5, last)])
    assert (
        measure(adapter, datetime(2026, 8, 4, 22, tzinfo=NY), datetime(2026, 8, 5, 22, tzinfo=NY))
        is None
    )


@given(
    first=st.floats(min_value=1, max_value=1e6, allow_nan=False, allow_infinity=False),
    growth=st.floats(min_value=0.9, max_value=1.1, allow_nan=False, allow_infinity=False),
)
def test_benchmark_ratio_is_invariant_to_price_scale(first: float, growth: float) -> None:
    inception = datetime(2026, 8, 4, 22, tzinfo=NY)
    now = datetime(2026, 8, 5, 22, tzinfo=NY)
    result = measure(DailyAdapter([daily(4, first), daily(5, first * growth)]), inception, now)
    scaled = measure(
        DailyAdapter([daily(4, first * 10), daily(5, first * growth * 10)]), inception, now
    )
    assert result == pytest.approx(growth - 1)
    assert scaled == pytest.approx(result)


@pytest.mark.parametrize("existing", [False, True])
def test_broker_wires_benchmark_only_with_existing_inception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    existing: bool,
) -> None:
    inception = datetime(2026, 8, 4, 22, tzinfo=NY)
    now = datetime(2026, 8, 6, 22, tzinfo=NY)
    path = tmp_path / "equity.json"
    curve = JsonFileEquityCurve(path)
    if existing:
        curve.save(
            [
                EquityPoint(
                    timestamp=inception,
                    equity=100_000,
                    cash=100_000,
                    n_positions=0,
                    return_since_start=0,
                )
            ]
        )
    account = AlpacaAccount(
        equity=Decimal("110000"), cash=Decimal("110000"), buying_power=Decimal("110000")
    )
    adapter = DailyAdapter([])
    helper = Mock(return_value=0.21)

    class Clock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return now

    monkeypatch.setattr(paper_broker, "datetime", Clock)
    monkeypatch.setattr(paper_broker, "EQUITY_CURVE", path)
    monkeypatch.setattr(
        paper_broker,
        "get_settings",
        lambda: SimpleNamespace(alpaca_api_key="", alpaca_secret_key=""),
    )
    monkeypatch.setattr(
        paper_broker, "JsonFilePaperPortfolio", lambda _p: SimpleNamespace(positions=lambda: [])
    )
    monkeypatch.setattr(paper_broker, "build_data_adapter", lambda _s: adapter)
    monkeypatch.setattr(
        paper_broker, "AlpacaBroker", lambda *_args: SimpleNamespace(account=lambda: account)
    )
    monkeypatch.setattr(paper_broker, "reconcile", lambda *_args: [])
    monkeypatch.setattr(paper_broker, "current_git_revision", lambda: "a" * 40)
    monkeypatch.setattr(paper_broker, "fetch_benchmark_return", helper)
    paper_broker.main()
    point = curve.all()[-1]
    if existing:
        helper.assert_called_once_with(adapter, inception, now, git_commit_hash="a" * 40)
        assert point.benchmark_return_since_start == pytest.approx(0.21)
        assert point.alpha_since_start == pytest.approx(-0.11)
    else:
        helper.assert_not_called()
        assert point.benchmark_return_since_start is None
        assert point.alpha_since_start is None
    assert adapter.requests == []


def test_benchmark_holiday_does_not_substitute_previous_friday() -> None:
    adapter = DailyAdapter([daily(3, 100, month=9), daily(4, 110, month=9)])
    assert (
        measure(adapter, datetime(2026, 9, 3, 22, tzinfo=NY), datetime(2026, 9, 7, 22, tzinfo=NY))
        is None
    )  # Labor Day.


def test_benchmark_early_close_remains_unmeasured_before_regular_cutoff() -> None:
    adapter = DailyAdapter([daily(25, 100, month=11), daily(27, 110, month=11)])
    assert (
        measure(
            adapter, datetime(2026, 11, 25, 22, tzinfo=NY), datetime(2026, 11, 27, 14, tzinfo=NY)
        )
        is None
    )
    assert adapter.requests == []


def test_benchmark_weekend_inception_uses_prior_friday() -> None:
    adapter = DailyAdapter([daily(7, 100), daily(10, 110)])
    assert measure(
        adapter, datetime(2026, 8, 8, 22, tzinfo=NY), datetime(2026, 8, 10, 22, tzinfo=NY)
    ) == pytest.approx(0.10)


def test_benchmark_submicrosecond_session_labels_are_unmeasured() -> None:
    bars = [
        daily(day, 100 + day).model_copy(
            update={
                "timestamp_utc": pd.Timestamp(datetime(2026, 8, day, tzinfo=NY))
                + pd.Timedelta(1, unit="ns"),
            }
        )
        for day in [4, 5, 6]
    ]
    assert (
        measure(
            DailyAdapter(bars),
            datetime(2026, 8, 4, 22, tzinfo=NY),
            datetime(2026, 8, 6, 22, tzinfo=NY),
        )
        is None
    )
