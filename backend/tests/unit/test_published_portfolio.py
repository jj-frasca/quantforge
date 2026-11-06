"""Independent fixed-unit cash oracles for ADR-417 (no network)."""

import importlib
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.models import PriceBar
from app.research.fundamentals.record import FundamentalRecord


def api() -> ModuleType:
    return importlib.import_module("app.research.cross_sectional.published_portfolio")


def record(symbol: str, cik: int, score: float | None) -> FundamentalRecord:
    return FundamentalRecord(
        symbol=symbol,
        cik=cik,
        fiscal_year=2025,
        quality_score=score,
        value_score=1.0,
        combined_score=score,
        f_score=5,
        gross_profitability=0.1,
    )


def test_selection_ceil_quintile_and_ties() -> None:
    rows = [record(f"S{i}", 10 - i, 0.5) for i in range(6)]
    rows += [record("NO", 99, None), record("OUT", 100, 1.0)]
    result = api().select_portfolio(rows, tuple([f"S{i}" for i in range(6)] + ["NO"]))
    assert result.eligible == tuple(f"S{i}" for i in range(6))
    assert result.selected == ("S5", "S4")
    assert api().select_portfolio(list(reversed(rows)), result.eligible) == result


@pytest.mark.parametrize(
    "rows",
    [
        [record("A", 1, 0.5), record("A", 2, 0.7)],
        [record("A", 1, 0.5), record("B", 1, 0.7)],
    ],
)
def test_selection_refuses_identity_ambiguity(rows: list[FundamentalRecord]) -> None:
    with pytest.raises(ValueError, match="identity"):
        api().select_portfolio(rows, ("A", "B"))


def test_selection_refuses_empty_and_duplicate_roster() -> None:
    with pytest.raises(ValueError):
        api().select_portfolio([], ("A",))
    with pytest.raises(ValueError):
        api().select_portfolio([record("A", 1, 0.5)], ("A", "A"))


def test_funded_account_exact_units_drift_costs_and_drawdown() -> None:
    prices = pd.DataFrame({"A": [10.0, 20.0, 15.0], "B": [20.0, 10.0, 20.0]})
    result = api().funded_hold(prices, cost_rate=0.001)
    ua, ub = 0.5 / (10 * 1.001), 0.5 / (20 * 1.001)
    marks = [ua * a + ub * b for a, b in zip(prices.A, prices.B, strict=True)]
    terminal = marks[-1] * 0.999
    assert result.equity == pytest.approx((1.0, *marks, terminal))
    assert result.net_return == pytest.approx(terminal - 1)
    assert result.gross_return == pytest.approx(0.25)
    assert result.turnover == pytest.approx(1 / 1.001 + marks[-1])
    assert result.fees == pytest.approx(0.001 * result.turnover)
    path = np.array(result.equity)
    assert result.max_drawdown == pytest.approx(min(path / np.maximum.accumulate(path) - 1))
    assert terminal != pytest.approx(1.125)  # daily rebalanced 50/50 is a different policy


@pytest.mark.parametrize("values", [[1.0, np.nan], [1.0, 0.0], [1.0, np.inf]])
def test_account_refuses_bad_prices(values: list[float]) -> None:
    with pytest.raises(ValueError):
        api().funded_hold(pd.DataFrame({"A": values}), cost_rate=0.001)


@pytest.mark.parametrize("cost", [-0.01, float("nan"), float("inf"), 1.0, True])
def test_account_refuses_invalid_costs(cost: float) -> None:
    with pytest.raises(ValueError):
        api().funded_hold(pd.DataFrame({"A": [1.0, 2.0]}), cost_rate=cost)


def test_account_refuses_empty_singleton_and_reversed_calendar() -> None:
    for prices in [
        pd.DataFrame(),
        pd.DataFrame({"A": [1.0]}),
        pd.DataFrame({"A": [1.0, 2.0]}, index=[2, 1]),
    ]:
        with pytest.raises(ValueError):
            api().funded_hold(prices, cost_rate=0.001)


@given(
    st.lists(
        st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=20,
    ),
    st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=40, deadline=None)
def test_cost_monotonicity_funding_and_terminal_identity(values: list[float], cost: float) -> None:
    prices = pd.DataFrame({"A": values, "B": list(reversed(values))})
    result = api().funded_hold(prices, cost_rate=cost)
    higher = api().funded_hold(prices, cost_rate=cost + 0.001)
    oracle = sum(prices.iloc[-1] / prices.iloc[0]) / 2
    assert result.net_return + 1 == pytest.approx(oracle * (1 - cost) / (1 + cost))
    assert result.equity[1] + cost / (1 + cost) == pytest.approx(1.0)
    assert higher.net_return <= result.net_return
    assert -1 < result.max_drawdown <= 0


def synthetic_provider(symbol: str) -> list[PriceBar]:
    from datetime import UTC, datetime

    from tests.fixtures.synthetic.builders import clean_series

    return [
        b
        for b in clean_series(symbol, n=57, start=datetime(2026, 8, 19, tzinfo=UTC))
        if b.timestamp_utc.date().isoformat() != "2026-09-07"
    ]


def test_one_attempt_complete_source_and_cost_matched_controls(tmp_path: Path) -> None:
    calls = []

    def provider(symbol: str) -> list[PriceBar]:
        calls.append(symbol)
        return synthetic_provider(symbol)

    selection = api().PortfolioSelection(("A", "B"), ("A",))
    result = api().evaluate_once(
        tmp_path / "new",
        selection,
        provider,
        adapter_version="synthetic",
        revision="a" * 40,
        context={},
    )
    assert calls == ["A", "B", "SPY"]
    assert result["status"] == "COMPLETE"
    assert result["screen_passed"] is False  # exact tied controls cannot beat each other
    assert len(list((tmp_path / "new").glob("source-*.json"))) == 3
    with pytest.raises(FileExistsError):
        api().evaluate_once(
            tmp_path / "new",
            selection,
            provider,
            adapter_version="synthetic",
            revision="a" * 40,
            context={},
        )
    assert len(calls) == 3


@pytest.mark.parametrize("failure", ["fetch", "calendar", "quality"])
def test_first_failure_freezes_unevaluable_no_partial_returns(tmp_path: Path, failure: str) -> None:
    import json

    calls = []

    def provider(symbol: str) -> list[PriceBar]:
        calls.append(symbol)
        if failure == "fetch":
            raise OSError("vendor unavailable")
        bars = synthetic_provider(symbol)
        return bars[:-1] if failure == "calendar" else []

    root = tmp_path / "new"
    result = api().evaluate_once(
        root,
        api().PortfolioSelection(("A", "B"), ("A",)),
        provider,
        adapter_version="synthetic",
        revision="a" * 40,
        context={},
    )
    assert result["status"] == "UNEVALUABLE"
    assert calls == ["A"]
    assert "accounts" not in result
    assert json.loads((root / "start.json").read_text())["selection"]["selected"] == ["A"]
    assert json.loads((root / "result.json").read_text()) == result


def test_calendar_matches_session_dates_across_dst() -> None:
    bars = synthetic_provider("A")
    from datetime import timedelta

    shifted = [
        b.model_copy(
            update={
                "timestamp_utc": b.timestamp_utc
                + timedelta(hours=4 if b.timestamp_utc.month < 11 else 5)
            }
        )
        for b in bars
    ]
    assert api().session_closes(shifted).index.equals(api().expected_sessions())


def test_archival_driver_refuses_substituted_input_before_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = importlib.import_module("scripts.published_quality_value_study")
    monkeypatch.setattr(driver.subprocess, "check_output", lambda *a, **k: b"[]")
    with pytest.raises(ValueError, match="hash"):
        driver.archived_inputs()


def test_final_new_high_preserves_exit_fee_drawdown() -> None:
    result = api().funded_hold(pd.DataFrame({"A": [1.0, 2.0]}), cost_rate=0.001)
    assert result.equity == pytest.approx((1.0, 1 / 1.001, 2 / 1.001, 2 * 0.999 / 1.001))
    assert result.max_drawdown == pytest.approx(-0.001)


def test_failed_quality_report_is_preserved(tmp_path: Path) -> None:
    import json

    root = tmp_path / "new"
    api().evaluate_once(
        root,
        api().PortfolioSelection(("A",), ("A",)),
        lambda s: [],
        adapter_version="synthetic",
        revision="a" * 40,
        context={},
    )
    report = json.loads((root / "quality-0000.json").read_text())
    assert report["passed"] is False
    assert any(i["check"] == "insufficient_data" for i in report["issues"])
