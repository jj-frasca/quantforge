"""ADR-380: parser-derived profit cannot overflow into a finite quality claim."""

import importlib
import json
import math
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.data.fundamentals import FundamentalsHistory, parse_company_facts_history
from app.data.models import DataQualityReport
from app.data.sources.edgar import SecEdgarFundamentalsSource, SicClassification
from app.research.dataset import ResearchDataset
from app.research.fundamentals.distress import make_distress_provider
from app.research.fundamentals.record import FundamentalRecord
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import make_value_provider
from app.research.lab.value_wiring import make_hunt_value_provider


def _facts(revenue: float | int, cogs: float, direct: float | None = None) -> dict[str, Any]:
    def row(value: float | int, year: int) -> dict[str, Any]:
        return {"val": value, "fy": year, "fp": "FY", "form": "10-K", "accn": "synthetic"}

    gaap = {
        "Revenues": {"units": {"USD": [row(1.0, 2023), row(revenue, 2024)]}},
        "CostOfRevenue": {"units": {"USD": [row(-2.0, 2023), row(cogs, 2024)]}},
    }
    if direct is not None:
        gaap["GrossProfit"] = {"units": {"USD": [row(direct, 2024)]}}
    return {"cik": 1, "entityName": "Synthetic", "facts": {"us-gaap": gaap}}


@pytest.mark.parametrize(("revenue", "cogs"), [(1e308, -1e308), (-1e308, 1e308)])
def test_derived_gross_profit_overflow_refuses_before_quality_scoring(
    revenue: float, cogs: float
) -> None:
    with pytest.raises(OverflowError, match="gross profit"):
        parse_company_facts_history(_facts(revenue, cogs), "SYNTH")


@settings(max_examples=100, deadline=None)
@example(revenue=sys.float_info.max, cogs=-sys.float_info.max)
@example(revenue=-sys.float_info.max, cogs=sys.float_info.max)
@given(
    revenue=st.floats(allow_nan=False, allow_infinity=False),
    cogs=st.floats(allow_nan=False, allow_infinity=False),
)
def test_finite_derived_profit_or_exact_out_of_range_refusal(revenue: float, cogs: float) -> None:
    exact = Fraction.from_float(revenue) - Fraction.from_float(cogs)
    try:
        history = parse_company_facts_history(_facts(revenue, cogs), "SYNTH")
    except OverflowError:
        assert not math.isfinite(revenue - cogs)
        assert abs(exact) > Fraction.from_float(sys.float_info.max)
    else:
        profit = history.years[-1].gross_profit
        assert profit is not None and math.isfinite(profit)
        assert profit.hex() == (revenue - cogs).hex()


@pytest.mark.parametrize("direct", [0.0, -42.0, 42.0])
def test_direct_gross_profit_keeps_precedence_over_unused_overflow(direct: float) -> None:
    history = parse_company_facts_history(_facts(1e308, -1e308, direct), "SYNTH")
    assert history.years[-1].gross_profit == direct


def _history_provider(revenue: float, cogs: float) -> Callable[[str], FundamentalsHistory]:
    def fetch_json(url: str) -> dict[str, Any]:
        if "company_tickers" in url:
            return {"0": {"ticker": "SYNTH", "cik_str": 1}}
        return _facts(revenue, cogs)

    return SecEdgarFundamentalsSource(user_agent="synthetic", fetcher=fetch_json).fetch_history


def _provider(
    kind: str, history_provider: Callable[[str], FundamentalsHistory]
) -> Callable[[str], Any]:
    if kind == "value":
        return make_value_provider(history_provider, lambda symbol: [])
    if kind == "hunt_value":
        return make_hunt_value_provider(history_provider, lambda symbol: pd.DataFrame())
    return make_distress_provider(history_provider)


@pytest.mark.parametrize("kind", ["value", "hunt_value", "distress"])
@pytest.mark.parametrize(("revenue", "cogs"), [(1e308, -1e308), (-1e308, 1e308)])
def test_actual_history_providers_propagate_derived_profit_refusal(
    kind: str, revenue: float, cogs: float
) -> None:
    provider = _provider(kind, _history_provider(revenue, cogs))
    with pytest.raises(OverflowError, match="gross profit"):
        provider("SYNTH")


@pytest.mark.parametrize("kind", ["value", "hunt_value", "distress"])
@pytest.mark.parametrize("error_type", [ValueError, KeyError, OSError])
def test_history_provider_keeps_existing_availability_fallback(
    kind: str, error_type: type[Exception]
) -> None:
    def unavailable(symbol: str) -> FundamentalsHistory:
        raise error_type("synthetic unavailable history")

    assert _provider(kind, unavailable)("SYNTH") is None


@pytest.mark.parametrize("kind", ["value", "hunt_value", "distress"])
def test_derived_profit_refusal_is_universe_error_before_search(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    frame = pd.DataFrame(
        {"close": [100.0, 101.0]}, index=pd.date_range("2024-01-01", periods=2, tz="UTC")
    )
    dataset = ResearchDataset(
        frame=frame,
        quality_report=DataQualityReport(
            symbol="SYNTH", source="yfinance", checked_at=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="synthetic",
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 3, tzinfo=UTC),
        git_commit_hash="a" * 40,
    )
    searches: list[bool] = []

    def forbidden_search(*args: object, **kwargs: object) -> None:
        searches.append(True)
        raise ValueError("search must not be invoked")

    monkeypatch.setattr("app.research.lab.universe.run_search", forbidden_search)
    provider = _provider(kind, _history_provider(1e308, -1e308))
    arguments = (
        {"distress_provider": provider} if kind == "distress" else {"value_provider": provider}
    )
    result = run_universe_hunt(["SYNTH"], ["sma"], lambda symbol: dataset, **arguments)
    assert searches == []
    assert result.experiments == [] and result.filtered == {}
    assert set(result.errors) == {"SYNTH"}
    assert result.errors["SYNTH"].startswith("OverflowError:")


@pytest.mark.parametrize("mode", ["derived", "raw_conversion"])
def test_actual_sweep_counts_overflow_and_scores_only_later_valid_company(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")
    original_compute = sweep.compute_fundamental_record
    scored: list[str] = []

    def fetch_history(symbol: str) -> FundamentalsHistory:
        facts = _facts(1e308, -1e308) if mode == "derived" else _facts(10**400, 0.0)
        return parse_company_facts_history(facts if symbol == "BAD" else _facts(2.0, 1.0), symbol)

    source = SimpleNamespace(all_tickers=lambda: ["BAD", "GOOD"], fetch_history=fetch_history)
    monkeypatch.setattr(sweep, "SecEdgarFundamentalsSource", lambda **kwargs: source)
    monkeypatch.setattr(sweep, "YFinanceAdapter", lambda **kwargs: object())
    monkeypatch.setattr(
        sweep, "_join_prices", lambda adapter, symbol, history, now: (history, None)
    )
    monkeypatch.setattr(
        sweep,
        "_sic_classification",
        lambda edgar, symbol: SicClassification(code=None, description=None),
    )
    monkeypatch.setattr(sweep.time, "sleep", lambda seconds: None)

    def compute(history: FundamentalsHistory, *args: Any) -> FundamentalRecord:
        scored.append(history.symbol)
        return original_compute(history, *args)

    monkeypatch.setattr(sweep, "compute_fundamental_record", compute)
    output = tmp_path / "output"
    monkeypatch.setattr(sweep.sys, "argv", ["fundamental_sweep", "0", "1", str(output)])
    sweep.main()
    assert scored == ["GOOD"]
    rows = json.loads((output / "fundamentals_shard_0.json").read_text())
    assert [row["symbol"] for row in rows] == ["GOOD"]
    assert "1 error(s)" in capsys.readouterr().out


@pytest.mark.parametrize("error_type", [ZeroDivisionError, FloatingPointError, ArithmeticError])
def test_sweep_keeps_unrelated_arithmetic_errors_propagating(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, error_type: type[Exception]
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")

    def fetch_history(symbol: str) -> FundamentalsHistory:
        raise error_type("unrelated arithmetic failure")

    source = SimpleNamespace(all_tickers=lambda: ["BAD"], fetch_history=fetch_history)
    monkeypatch.setattr(sweep, "SecEdgarFundamentalsSource", lambda **kwargs: source)
    monkeypatch.setattr(sweep, "YFinanceAdapter", lambda **kwargs: object())
    monkeypatch.setattr(sweep.time, "sleep", lambda seconds: None)
    output = tmp_path / "output"
    monkeypatch.setattr(sweep.sys, "argv", ["fundamental_sweep", "0", "1", str(output)])
    with pytest.raises(error_type, match="unrelated arithmetic"):
        sweep.main()
    assert not output.exists()
