"""ADR-398: computed multiples cannot erase invalid evidence into finite ranks."""

import importlib
import math
import re
from datetime import date, datetime
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from tests.unit.test_valuation_multiples import _history

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.data.sources.edgar import SicClassification
from app.research.fundamentals.record import compute_fundamental_record
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation.multiples import _ranked, compute_multiples
from app.research.valuation.score import score_valuation

CONSUMERS = [compute_multiples, score_valuation, compute_fundamental_record]


def _bad_history(metric: str = "P/S", location: str = "historical") -> FundamentalsHistory:
    if location == "historical":
        old = (
            {"price": 1e200, "shares_diluted": 1e200, "revenue": 1e308}
            if metric == "P/S"
            else {"price": 1e308, "eps": 1e-308, "revenue": 1.0}
        )
        latest = (
            {"revenue": 1.0, "shares_diluted": 1.0}
            if metric == "P/S"
            else {"revenue": 1.0, "eps": 1.0}
        )
    else:
        old = {"revenue": 1.0}
        latest = (
            {"revenue": 1e308, "shares_diluted": 1e308}
            if metric == "P/S"
            else {"revenue": 1.0, "eps": 1e-308}
        )
    return _history(
        [
            AnnualFundamentals(fiscal_year=2023, **old),
            AnnualFundamentals(fiscal_year=2024, **old),
            AnnualFundamentals(fiscal_year=2025, **latest),
        ]
    )


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("metric", ["P/E", "P/S"])
@pytest.mark.parametrize("location", ["current", "historical"])
def test_actual_computed_multiples_refuse_before_erasure(
    consumer, metric: str, location: str
) -> None:
    h = _bad_history(metric, location)
    name = f"{location} {metric}" + ("[0]" if location == "historical" else "")
    with pytest.raises(
        ValueError, match=re.escape(name + " must be finite for valuation multiples")
    ):
        consumer(h, 1e308 if location == "current" else 1e100)


def test_finite_historical_ps_exact_witness_refuses_instead_of_wrong_cheapness() -> None:
    h = _bad_history()
    current = Fraction(1e100)
    exact = [
        Fraction(y.price) * Fraction(y.shares_diluted) / Fraction(y.revenue) for y in h.years[:2]
    ]
    assert all(
        math.isfinite(y.price) and math.isfinite(y.shares_diluted) and math.isfinite(y.revenue)
        for y in h.years[:2]
    )
    assert all(math.isinf(y.price * y.shares_diluted / y.revenue) for y in h.years[:2])
    assert all(math.isfinite(float(x)) and x < current for x in exact)
    assert sum(x < current for x in exact) / len(exact) == 1.0
    with pytest.raises(ValueError, match=r"historical P/S\[0\] must be finite"):
        score_valuation(h, 1e100)


@pytest.mark.parametrize("metric", ["P/E", "P/S"])
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_ranked_current_nonfinite_refuses_even_empty_history(metric: str, bad: float) -> None:
    flags: list[str] = []
    with pytest.raises(ValueError, match=re.escape(f"current {metric} must be finite")):
        _ranked(bad, [], metric, flags)
    assert flags == []


@pytest.mark.parametrize("metric", ["P/E", "P/S"])
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("current", [None, 1.0])
@pytest.mark.parametrize("index", [0, 1])
def test_ranked_history_refuses_before_absent_or_thin_shortcuts(
    metric: str, bad: float, current: float | None, index: int
) -> None:
    flags: list[str] = []
    series = [1.0] * index + [bad]
    with pytest.raises(ValueError, match=re.escape(f"historical {metric}[{index}] must be finite")):
        _ranked(current, series, metric, flags)
    assert flags == []


@pytest.mark.parametrize("metric", ["P/E", "P/S"])
@pytest.mark.parametrize("absent", [False, True])
def test_actual_thin_and_missing_current_still_refuse(metric: str, absent: bool) -> None:
    h = _bad_history(metric)
    rows = list(h.years[1:])
    if absent:
        rows[-1] = rows[-1].model_copy(
            update={"eps" if metric == "P/E" else "shares_diluted": None}
        )
    with pytest.raises(ValueError, match=re.escape(f"historical {metric}[0] must be finite")):
        compute_multiples(_history(rows), 10.0)


def test_current_guard_precedes_history_and_pe_precedes_ps() -> None:
    with pytest.raises(ValueError, match="current P/E must be finite"):
        _ranked(math.inf, [math.nan], "P/E", [])
    h = _bad_history("P/E")
    latest = h.years[-1].model_copy(update={"shares_diluted": 1e308, "revenue": 1.0})
    with pytest.raises(ValueError, match=r"historical P/E\[0\] must be finite"):
        compute_multiples(_history([*h.years[:-1], latest]), 1e100)


@pytest.mark.parametrize("current", [None, 0.0, -1.0, 1.0])
@pytest.mark.parametrize("series", [[], [0.0], [-1.0, 0.0, 1.0], [1.0, 1.0]])
def test_finite_missing_thin_ties_and_flags_retain_native_behavior(
    current: float | None, series: list[float]
) -> None:
    flags = ["prior flag"]
    actual = _ranked(current, series, "P/E", flags)
    if current is None:
        assert actual is None and flags == ["prior flag"]
    elif len(series) < 2:
        assert actual is None and flags == [
            "prior flag",
            "insufficient P/E history for a percentile",
        ]
    else:
        assert actual == sum(x < current for x in series) / len(series)
        assert flags == ["prior flag"]


@pytest.mark.parametrize("metric", ["P/E", "P/S"])
def test_ineligible_rows_remain_excluded_without_arithmetic(metric: str) -> None:
    h = _bad_history(metric)
    field = "eps" if metric == "P/E" else "shares_diluted"
    h = _history([y.model_copy(update={field: -math.inf}) for y in h.years[:2]] + [h.years[-1]])
    result = compute_multiples(h, 10.0)
    assert getattr(result, "pe_history_n" if metric == "P/E" else "ps_history_n") == 0


@given(
    price=st.floats(min_value=1e-200, max_value=1e200, allow_nan=False, allow_infinity=False),
    shares=st.floats(min_value=1e-200, max_value=1e200, allow_nan=False, allow_infinity=False),
    revenue=st.floats(min_value=1e-200, max_value=1e200, allow_nan=False, allow_infinity=False),
)
@example(price=1e200, shares=1e200, revenue=1e200)
def test_computed_history_ps_is_finite_or_refuses_without_changing_native_rank(
    price: float, shares: float, revenue: float
) -> None:
    h = _history(
        [
            AnnualFundamentals(
                fiscal_year=2024, price=price, shares_diluted=shares, revenue=revenue
            ),
            AnnualFundamentals(fiscal_year=2025, price=10.0, shares_diluted=1.0, revenue=1.0),
        ]
    )
    ratio = price * shares / revenue
    if not math.isfinite(ratio):
        with pytest.raises(ValueError, match=r"historical P/S\[0\] must be finite"):
            compute_multiples(h, 10.0)
    else:
        result = compute_multiples(h, 10.0)
        assert result.ps_ratio == 10.0 and result.ps_history_n == 2
        assert result.ps_percentile == ((ratio < 10.0) + (10.0 < 10.0)) / 2


@pytest.mark.parametrize("enabled", [False, True])
def test_real_provider_refusal_becomes_hunt_error_before_search(enabled: bool) -> None:
    h = _bad_history()
    events: list[str] = []

    def history(symbol: str) -> FundamentalsHistory:
        events.append("history")
        return h

    def prices(symbol: str) -> list[tuple[date, float]]:
        events.append("prices")
        return [(date(2025, 12, 31), 1e100)]

    def downstream(symbol: str) -> None:
        events.append("downstream")
        raise ValueError("DOWNSTREAM_SENTINEL_NO_SEARCH")

    provider = make_value_provider(history, prices)
    result = run_universe_hunt(
        ["AAPL"],
        ["sma"],
        downstream,
        value_provider=provider,
        value_config=ValueGateConfig() if enabled else None,
    )
    assert "historical P/S[0] must be finite" in result.errors["AAPL"]
    assert result.experiments == [] and result.filtered == {}
    assert events == ["history", "prices"]


def test_multiple_refusal_aborts_real_mocked_sweep_before_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")
    events: list[str] = []

    def fetch(symbol: str) -> FundamentalsHistory:
        events.append(f"fetch:{symbol}")
        return _bad_history().model_copy(update={"symbol": symbol})

    def join(adapter: object, symbol: str, history: FundamentalsHistory, now: datetime) -> tuple:
        events.append(f"prices:{symbol}")
        return history, 1e100

    def classify(edgar: object, symbol: str) -> SicClassification:
        events.append(f"sic:{symbol}")
        return SicClassification(code=None, description=None)

    monkeypatch.setattr(
        sweep,
        "SecEdgarFundamentalsSource",
        lambda **kwargs: SimpleNamespace(all_tickers=lambda: ["BAD", "GOOD"], fetch_history=fetch),
    )
    monkeypatch.setattr(sweep, "YFinanceAdapter", lambda **kwargs: object())
    monkeypatch.setattr(sweep, "_join_prices", join)
    monkeypatch.setattr(sweep, "_sic_classification", classify)
    monkeypatch.setattr(sweep.time, "sleep", lambda seconds: None)
    output = tmp_path / "output"
    monkeypatch.setattr(sweep.sys, "argv", ["fundamental_sweep", "0", "1", str(output)])
    with pytest.raises(ValueError, match=r"historical P/S\[0\] must be finite"):
        sweep.main()
    assert events == ["fetch:BAD", "prices:BAD", "sic:BAD"]
    assert not output.exists()
