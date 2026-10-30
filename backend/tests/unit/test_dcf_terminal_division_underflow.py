"""ADR-411: finite terminal division cannot erase nonzero cash flow."""

import math
import sys
from collections.abc import Callable
from datetime import date
from fractions import Fraction
from typing import NoReturn

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.score import score_valuation

_ERROR = "^terminal_value must not underflow to zero for DCF$"


def _history(*, proxy: bool = False, count: int = 2, base: float = 1e-300) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="SYN",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=tuple(
            AnnualFundamentals(
                fiscal_year=2023 + i,
                period_end=date(2023 + i, 12, 31),
                revenue=100.0,
                eps=1.0,
                net_income=base if proxy else 1.0,
                free_cash_flow=None if proxy else base,
                shares_diluted=1.0,
                price=10.0,
            )
            for i in range(count)
        ),
    )


def _settings(
    *, terminal: float = 0.0, discount: float = 1e300, horizon: int = 0
) -> DcfAssumptions:
    return DcfAssumptions(
        discount_rate=discount,
        terminal_growth=terminal,
        min_growth=0.0,
        max_growth=0.0,
        projection_years=horizon,
    )


def _score(history: FundamentalsHistory, settings: DcfAssumptions) -> object:
    return score_valuation(history, 1.0, assumptions=settings)


@pytest.mark.parametrize("consume", [dcf_intrinsic_value, _score])
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0])
@pytest.mark.parametrize("horizon", [0, -1])
def test_nonzero_terminal_cash_flow_refuses_zero_finite_quotient(
    consume: Callable[[FundamentalsHistory, DcfAssumptions], object],
    count: int,
    proxy: bool,
    terminal: float,
    horizon: int,
) -> None:
    numerator = 1e-300 * (1.0 + terminal)
    denominator = 1e300 - terminal
    exact = Fraction(numerator) / Fraction(denominator)
    assert 0 < abs(exact) < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        consume(_history(proxy=proxy, count=count), _settings(terminal=terminal, horizon=horizon))


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0])
def test_custom_provider_propagates_terminal_loss_refusal(proxy: bool, terminal: float) -> None:
    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
        assumptions=_settings(terminal=terminal),
    )
    with pytest.raises(ValueError, match=_ERROR):
        provider("SYN")


@pytest.mark.parametrize("config", [None, ValueGateConfig()])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0])
def test_hunt_records_terminal_error_before_downstream_acquisition(
    config: ValueGateConfig | None, proxy: bool, terminal: float
) -> None:
    calls: list[str] = []

    def acquire(symbol: str) -> NoReturn:
        calls.append(symbol)
        raise AssertionError("must not acquire after terminal loss")

    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
        assumptions=_settings(terminal=terminal),
    )
    result = run_universe_hunt(
        ["SYN"], ["sma"], acquire, value_provider=provider, value_config=config
    )
    assert calls == []
    assert result.experiments == [] and result.filtered == {}
    assert result.errors == {"SYN": "ValueError: terminal_value must not underflow to zero for DCF"}


@pytest.mark.parametrize("proxy", [False, True])
def test_terminal_loss_refuses_even_when_period_accumulator_remains_nonzero(proxy: bool) -> None:
    terminal = math.nextafter(-1.0, 0.0)
    base, discount = 1e-210, 1e100
    numerator = base * (1.0 + terminal)
    exact = Fraction(numerator) / Fraction(discount - terminal)
    assert 0 < base / (1 + discount) < sys.float_info.min
    assert 0 < exact < Fraction(math.ulp(0.0)) / 2
    settings = _settings(terminal=terminal, discount=discount, horizon=1)
    history = _history(base=base, proxy=proxy)
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(history, settings)
    with pytest.raises(ValueError, match=_ERROR):
        score_valuation(history, 1e-310, assumptions=settings)


def test_terminal_refusal_precedes_later_zero_discount_factor_division() -> None:
    # Previously terminal_value became0 then final discount_factor became0 ->0/0.
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(_history(), _settings(horizon=-2))


@pytest.mark.parametrize("horizon", [0, -1, -2])
@pytest.mark.parametrize("proxy", [False, True])
def test_genuine_zero_terminal_numerator_preserves_zero(horizon: int, proxy: bool) -> None:
    result = dcf_intrinsic_value(
        _history(proxy=proxy), _settings(terminal=-1.0, discount=0.1, horizon=horizon)
    )
    assert result.intrinsic_value_per_share == 0.0
    assert result.assumptions.projection_years == horizon


@pytest.mark.parametrize("terminal,sign", [(0.0, 1.0), (-2.0, -1.0)])
def test_nonzero_subnormal_terminal_quotient_preserves_native_value(
    terminal: float, sign: float
) -> None:
    settings = _settings(terminal=terminal, discount=1e23)
    value = dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share
    expected = (1e-300 * (1.0 + terminal)) / (1e23 - terminal)
    assert value == expected and value is not None
    assert 0 < abs(value) < sys.float_info.min
    assert math.copysign(1.0, value) == sign


@pytest.mark.parametrize("horizon", [0, -1, -2])
def test_ordinary_no_loop_horizons_keep_native_terminal_arithmetic(horizon: int) -> None:
    settings = _settings(discount=0.1, horizon=horizon)
    value = dcf_intrinsic_value(_history(base=100.0), settings).intrinsic_value_per_share
    assert value == (100.0 / 0.1) / (1.1**horizon)


def test_finite_knobs_with_infinite_native_denominator_keep_existing_zero() -> None:
    settings = _settings(discount=1e308, terminal=-1e308)
    assert math.isinf(settings.discount_rate - settings.terminal_growth)
    assert dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share == 0.0


def test_unchecked_infinite_denominator_keeps_direct_and_later_metadata_policy() -> None:
    settings = _settings().model_copy(update={"discount_rate": math.inf})
    assert dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share == 0.0
    with pytest.raises(ValueError, match="finite"):
        score_valuation(_history(), 1.0, assumptions=settings)


def test_native_zero_terminal_denominator_still_raises_division_error() -> None:
    settings = _settings().model_copy(update={"discount_rate": 0.0})
    with pytest.raises(ZeroDivisionError):
        dcf_intrinsic_value(_history(), settings)


@given(
    base_exponent=st.integers(min_value=-1000, max_value=-700),
    discount_exponent=st.integers(min_value=700, max_value=1000),
    negative=st.booleans(),
    proxy=st.booleans(),
)
def test_exact_nonzero_terminal_quotient_below_half_minimum_float_refuses(
    base_exponent: int, discount_exponent: int, negative: bool, proxy: bool
) -> None:
    base = math.ldexp(1.0, base_exponent)
    discount = math.ldexp(1.0, discount_exponent)
    terminal = -2.0 if negative else 0.0
    numerator, denominator = base * (1.0 + terminal), discount - terminal
    exact = Fraction(numerator) / Fraction(denominator)
    assert 0 < abs(exact) < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(
            _history(base=base, proxy=proxy), _settings(discount=discount, terminal=terminal)
        )


@given(base=st.integers(min_value=1, max_value=100000), horizon=st.integers(-5, 0))
def test_ordinary_no_loop_terminal_perpetuity_matches_native_oracle(
    base: int, horizon: int
) -> None:
    settings = _settings(discount=0.125, horizon=horizon)
    result = dcf_intrinsic_value(_history(base=float(base)), settings)
    assert result.intrinsic_value_per_share == (float(base) / 0.125) / (1.125**horizon)
