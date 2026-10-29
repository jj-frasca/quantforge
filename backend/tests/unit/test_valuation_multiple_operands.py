"""ADR-401: finite source operands at the original numerical consumption sites."""

import math
import re
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_valuation_multiples import _three_year

from app.data.fundamentals import FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation.multiples import compute_multiples
from app.research.valuation.score import score_valuation


def _history(*changes: tuple[int, str, object]) -> FundamentalsHistory:
    payload = _three_year().model_dump()
    for index, field, value in changes:
        payload["years"][index][field] = value
    # The witness must cross ordinary input validation, not an unchecked copy.
    return FundamentalsHistory.model_validate(payload)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize(
    ("changes", "label", "bad_price"),
    [
        ([(2, "eps")], "current P/E EPS", False),
        ([(0, "eps")], "historical P/E EPS", False),
        ([(0, "price")], "historical P/E price", False),
        ([], "current P/E price", True),
        ([(2, "revenue")], "current P/S revenue", False),
        ([(2, "shares_diluted")], "current P/S shares", False),
        ([(0, "shares_diluted")], "historical P/S shares", False),
        ([(0, "revenue")], "historical P/S revenue", False),
        ([(2, "eps", None)], "current P/S price", True),
    ],
)
def test_reached_nonfinite_operand_refuses_before_numeric_use(
    changes: list[tuple], label: str, bad_price: bool, bad: float
) -> None:
    updates = [(c[0], c[1], bad if len(c) == 2 else c[2]) for c in changes]
    h = _history(*updates)
    with pytest.raises(ValueError, match=re.escape(label + " operand must be finite")):
        compute_multiples(h, bad if bad_price else 55.0)


@pytest.mark.parametrize(
    "consumer", [compute_multiples, score_valuation, compute_fundamental_record]
)
@pytest.mark.parametrize("index", [0, 2])
def test_validated_infinite_eps_cannot_become_finite_maximum_cheapness(
    consumer, index: int
) -> None:
    h = _history((index, "eps", math.inf))
    assert math.isinf(h.years[index].eps)
    label = "current" if index == 2 else "historical"
    with pytest.raises(ValueError, match=label + " P/E EPS operand must be finite"):
        consumer(h, 55.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("price", [None, 0.0, -1.0])
def test_historical_fields_behind_skipped_price_remain_dormant(
    bad: float, price: float | None
) -> None:
    h = _history(
        (0, "price", price), (0, "eps", bad), (0, "shares_diluted", bad), (0, "revenue", bad)
    )
    control = _history((0, "price", price))
    assert compute_multiples(h, 55.0) == compute_multiples(control, 55.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("shares", [None, 0.0, -1.0])
def test_historical_revenue_behind_skipped_shares_remains_dormant(
    bad: float, shares: float | None
) -> None:
    h = _history((0, "shares_diluted", shares), (0, "revenue", bad))
    control = _history((0, "shares_diluted", shares))
    assert compute_multiples(h, 55.0) == compute_multiples(control, 55.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_current_revenue_behind_missing_shares_remains_dormant(bad: float) -> None:
    h = _history((2, "price", None), (2, "shares_diluted", None), (2, "revenue", bad))
    control = _history((2, "price", None), (2, "shares_diluted", None))
    assert compute_multiples(h, 55.0) == compute_multiples(control, 55.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("revenue", [0.0, -1.0])
def test_current_shares_behind_nonpositive_revenue_remain_dormant(
    bad: float, revenue: float
) -> None:
    h = _history((2, "price", None), (2, "shares_diluted", bad), (2, "revenue", revenue))
    control = _history((2, "price", None), (2, "shares_diluted", 1.0), (2, "revenue", revenue))
    assert compute_multiples(h, 55.0) == compute_multiples(control, 55.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_unused_current_price_remains_unconsumed_by_multiples(bad: float) -> None:
    h = _history((2, "eps", None), (2, "shares_diluted", None))
    assert compute_multiples(h, bad) == compute_multiples(h, 55.0)


def test_ps_revenue_then_price_then_shares_and_pe_stage_precedence() -> None:
    cases = [
        (_history((2, "eps", math.nan), (2, "revenue", math.nan)), math.nan, "current P/E EPS"),
        (
            _history((2, "eps", None), (2, "shares_diluted", math.nan), (2, "revenue", math.nan)),
            math.nan,
            "current P/S revenue",
        ),
        (
            _history((2, "eps", None), (2, "shares_diluted", math.nan)),
            math.nan,
            "current P/S price",
        ),
        (_history((2, "eps", None), (2, "shares_diluted", math.nan)), 55.0, "current P/S shares"),
        (_history((0, "eps", math.nan), (2, "revenue", math.nan)), 55.0, "historical P/E EPS"),
    ]
    for h, price, label in cases:
        with pytest.raises(ValueError, match=re.escape(label + " operand must be finite")):
            compute_multiples(h, price)


def test_existing_computed_overflow_precedes_later_ps_operand_refusal() -> None:
    h = _history((0, "price", 1e308), (0, "eps", 1e-308), (2, "revenue", math.nan))
    with pytest.raises(ValueError, match=r"historical P/E\[0\] must be finite"):
        compute_multiples(h, 55.0)


@pytest.mark.parametrize("enabled", [False, True])
def test_invalid_operand_real_provider_refuses_before_downstream_search(enabled: bool) -> None:
    h = _history((2, "eps", math.inf))
    events: list[str] = []

    def history(symbol: str):
        events.append("history")
        return h

    def prices(symbol: str):
        events.append("prices")
        return [(date(2025, 12, 31), 55.0)]

    provider = make_value_provider(history, prices)
    with pytest.raises(ValueError, match="current P/E EPS operand must be finite"):
        provider(h.symbol)
    assert events == ["history", "prices"]
    events.clear()

    def downstream(symbol: str):
        events.append("downstream")
        raise ValueError("DOWNSTREAM_NO_SEARCH")

    result = run_universe_hunt(
        [h.symbol],
        ["sma"],
        downstream,
        value_provider=provider,
        value_config=ValueGateConfig() if enabled else None,
    )
    assert "current P/E EPS operand must be finite" in result.errors[h.symbol]
    assert result.experiments == [] and result.filtered == {}
    assert events == ["history", "prices"]


@given(price=st.floats(min_value=-100, max_value=100), eps=st.floats(min_value=-100, max_value=100))
def test_finite_eps_ranking_retains_native_eligibility_and_strict_ties(
    price: float, eps: float
) -> None:
    h = _history(*[(i, "eps", eps) for i in range(3)])
    if eps > 0 and (
        not math.isfinite(price / eps) or any(not math.isfinite(y.price / eps) for y in h.years)
    ):
        with pytest.raises(ValueError, match="must be finite"):
            compute_multiples(h, price)
        return
    result = compute_multiples(h, price)
    if eps <= 0:
        assert result.pe_ratio is None and result.pe_percentile is None and result.pe_history_n == 0
    else:
        ratios = [y.price / eps for y in h.years]
        assert result.pe_ratio == price / eps
        assert result.pe_history_n == 3
        assert result.pe_percentile == sum(r < price / eps for r in ratios) / 3
