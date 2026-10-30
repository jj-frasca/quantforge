"""ADR-407: reached DCF denominators are finite source evidence."""

import math
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.score import score_valuation


def _history(
    shares: float | None, *, base: float | None = 12.0, proxy: bool = False
) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="TEST",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=(
            AnnualFundamentals(
                fiscal_year=2024,
                revenue=0.0,
                free_cash_flow=None if proxy else base,
                net_income=base if proxy else None,
                shares_diluted=shares,
            ),
        ),
    )


def _dcf(history: FundamentalsHistory) -> object:
    return dcf_intrinsic_value(history)


def _valuation(history: FundamentalsHistory) -> object:
    return score_valuation(history, 10.0)


def _record(history: FundamentalsHistory) -> object:
    return compute_fundamental_record(history, 10.0)


@pytest.mark.parametrize("consume", [_dcf, _valuation, _record])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("count", [1, 2])
def test_dcf_refuses_reached_nonfinite_shares(
    consume: Callable[[FundamentalsHistory], object], invalid: float, proxy: bool, count: int
) -> None:
    history = _history(invalid, proxy=proxy)
    if count == 2:
        latest = history.years[0]
        prior = latest.model_copy(update={"fiscal_year": 2023, "shares_diluted": 10.0})
        history = history.model_copy(update={"years": (prior, latest)})
    # Multi-year records run Piotroski first; its existing refusal keeps precedence.
    error = (
        r"^latest\.shares_diluted must be finite for Piotroski F-score$"
        if count == 2 and consume is _record
        else r"^shares_diluted for fiscal year 2024 must be finite for DCF$"
    )
    with pytest.raises(ValueError, match=error):
        consume(history)


@pytest.mark.parametrize("shares", [None, -1.0, -0.0, 0.0])
@pytest.mark.parametrize("proxy", [False, True])
def test_dcf_missing_or_finite_nonpositive_shares_keep_flagged_return(
    shares: float | None, proxy: bool
) -> None:
    result = dcf_intrinsic_value(_history(shares, proxy=proxy))
    assert result.intrinsic_value_per_share is None
    assert result.fcf_base == 12.0
    assert result.fcf_is_net_income_proxy is proxy
    assert result.flags[-1] == "shares outstanding unavailable — cannot value per share"


@pytest.mark.parametrize("base", [None, -1.0, -0.0, 0.0, -math.inf])
@pytest.mark.parametrize("shares", [math.nan, math.inf, -math.inf])
def test_dcf_earlier_base_returns_do_not_consume_shares(base: float | None, shares: float) -> None:
    result = dcf_intrinsic_value(_history(shares, base=base))
    assert result.intrinsic_value_per_share is None
    assert result.fcf_base == base
    assert result.flags[-1] == (
        "no free cash flow or net income to value"
        if base is None
        else "non-positive base cash flow — DCF not meaningful"
    )


def test_dcf_share_refusal_precedes_later_growth_calendar_error() -> None:
    single = _history(math.inf)
    row = single.years[0]
    history = single.model_copy(update={"years": (row, row)})
    with pytest.raises(ValueError, match=r"shares_diluted.*finite for DCF"):
        dcf_intrinsic_value(history)


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_dcf_does_not_consume_historical_shares_or_inactive_proxy(invalid: float) -> None:
    single = _history(10.0)
    latest = single.years[0].model_copy(update={"net_income": invalid})
    prior = latest.model_copy(update={"fiscal_year": 2023, "shares_diluted": invalid})
    history = single.model_copy(update={"years": (prior, latest)})
    result = dcf_intrinsic_value(history)
    assert result.intrinsic_value_per_share is not None
    assert math.isfinite(result.intrinsic_value_per_share)
    assert result.fcf_is_net_income_proxy is False


@given(
    base=st.floats(min_value=1.0, max_value=1e6),
    shares=st.floats(min_value=1.0, max_value=1e6),
)
def test_dcf_finite_shares_match_independent_perpetuity(base: float, shares: float) -> None:
    assumptions = DcfAssumptions(
        terminal_growth=0.0, min_growth=0.0, max_growth=0.0, projection_years=2
    )
    result = dcf_intrinsic_value(_history(shares, base=base), assumptions)
    assert result.intrinsic_value_per_share == pytest.approx(base / 0.10 / shares)
    assert result.fcf_base == base
    assert result.growth_rate_used == 0.0
