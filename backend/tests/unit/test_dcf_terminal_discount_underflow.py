"""ADR-412: final finite-factor terminal discounting cannot erase nonzero value."""

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

_ERROR = "^discounted_terminal_value must not underflow to zero for DCF$"


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
    *,
    terminal: float = 0.0,
    discount: float = 1e25,
    growth: float | None = None,
    horizon: int = 2,
) -> DcfAssumptions:
    growth = -discount if growth is None else growth
    return DcfAssumptions(
        discount_rate=discount,
        terminal_growth=terminal,
        min_growth=growth,
        max_growth=growth,
        projection_years=horizon,
    )


def _score(history: FundamentalsHistory, settings: DcfAssumptions) -> object:
    return score_valuation(history, 1.0, assumptions=settings)


@pytest.mark.parametrize("consume", [dcf_intrinsic_value, _score])
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0, -0.5])
def test_nonzero_terminal_value_refuses_zero_finite_discount_quotient(
    consume: Callable[[FundamentalsHistory, DcfAssumptions], object],
    count: int,
    proxy: bool,
    terminal: float,
) -> None:
    settings = _settings(terminal=terminal)
    base = 1e-300
    periods = [
        base * (1 + settings.min_growth) ** t / (1 + settings.discount_rate) ** t for t in (1, 2)
    ]
    assert periods == [-base, base] and sum(periods) == 0.0
    projected = base * (1 + settings.min_growth) ** 2
    terminal_value = projected * (1 + terminal) / (settings.discount_rate - terminal)
    factor = (1 + settings.discount_rate) ** 2
    exact = Fraction(terminal_value) / Fraction(factor)
    assert terminal_value != 0.0 and math.isfinite(factor)
    assert 0 < abs(exact) < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        consume(_history(proxy=proxy, count=count), settings)


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0, -0.5])
def test_custom_provider_propagates_terminal_discount_loss(proxy: bool, terminal: float) -> None:
    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
        assumptions=_settings(terminal=terminal),
    )
    with pytest.raises(ValueError, match=_ERROR):
        provider("SYN")


@pytest.mark.parametrize("config", [None, ValueGateConfig()])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("terminal", [0.0, -2.0, -0.5])
def test_hunt_records_terminal_discount_error_before_frame_acquisition(
    config: ValueGateConfig | None, proxy: bool, terminal: float
) -> None:
    calls: list[str] = []

    def acquire(symbol: str) -> NoReturn:
        calls.append(symbol)
        raise AssertionError("must not acquire after terminal discount loss")

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
    assert result.errors == {
        "SYN": "ValueError: discounted_terminal_value must not underflow to zero for DCF"
    }


@pytest.mark.parametrize("proxy", [False, True])
def test_terminal_discount_loss_refuses_nonzero_period_accumulator(proxy: bool) -> None:
    base, discount = 1e-200, 1e100
    settings = _settings(discount=discount, growth=0.0, horizon=1)
    history = _history(base=base, proxy=proxy)
    period = base / (1 + discount)
    terminal_value = base / discount
    assert period == 1e-300 and terminal_value != 0.0
    exact = Fraction(terminal_value) / Fraction(1 + discount)
    assert 0 < exact < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(history, settings)
    with pytest.raises(ValueError, match=_ERROR):
        score_valuation(history, 1e-300, assumptions=settings)


@pytest.mark.parametrize("proxy", [False, True])
def test_genuine_zero_terminal_value_keeps_native_cancelled_equity(proxy: bool) -> None:
    settings = _settings(terminal=-1.0)
    assert dcf_intrinsic_value(_history(proxy=proxy), settings).intrinsic_value_per_share == 0.0


@pytest.mark.parametrize("growth,sign", [(0.0, 1.0), (-2.0, -1.0)])
def test_nonzero_subnormal_terminal_discount_preserves_native_value(
    growth: float, sign: float
) -> None:
    base, discount = 1e-300, 1e10
    settings = _settings(discount=discount, growth=growth, horizon=1)
    projected = base * (1 + growth)
    period = projected / (1 + discount)
    terminal_value = projected / discount
    terminal_pv = terminal_value / (1 + discount)
    assert 0 < abs(terminal_pv) < sys.float_info.min
    assert math.copysign(1.0, terminal_pv) == sign
    value = dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share
    assert value == period + terminal_pv


@pytest.mark.parametrize("horizon", [0, -1])
def test_ordinary_no_loop_horizons_preserve_native_value(horizon: int) -> None:
    settings = _settings(discount=0.1, growth=0.0, horizon=horizon)
    value = dcf_intrinsic_value(_history(base=100.0), settings).intrinsic_value_per_share
    assert value == (100.0 / 0.1) / (1.1**horizon)


@pytest.mark.parametrize("horizon", [0, 1])
def test_unchecked_infinite_factor_keeps_prior_direct_and_metadata_policy(
    horizon: int,
) -> None:
    settings = _settings(growth=0.0, horizon=horizon).model_copy(update={"discount_rate": math.inf})
    assert dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share == 0.0
    with pytest.raises(ValueError, match="finite"):
        score_valuation(_history(), 1.0, assumptions=settings)


def test_native_power_failure_before_terminal_discount_still_propagates() -> None:
    settings = _settings(discount=1e200, growth=0.0, horizon=2)
    with pytest.raises(OverflowError):
        dcf_intrinsic_value(_history(base=1e300), settings)


def test_native_zero_period_factor_still_raises_before_terminal_discount() -> None:
    settings = _settings(discount=-1.0, terminal=-2.0, growth=0.0, horizon=1)
    with pytest.raises(ZeroDivisionError):
        dcf_intrinsic_value(_history(), settings)


@pytest.mark.parametrize("growth,sign", [(0.0, 1.0), (-2.0, -1.0)])
def test_period_only_subnormal_preserved_with_true_zero_terminal_value(
    growth: float, sign: float
) -> None:
    settings = _settings(discount=1e23, terminal=-1.0, growth=growth, horizon=1)
    value = dcf_intrinsic_value(_history(), settings).intrinsic_value_per_share
    assert value == sign * float.fromhex("0x0.0000000000002p-1022")


@given(
    base_exponent=st.integers(min_value=-1000, max_value=-900),
    discount_exponent=st.integers(min_value=200, max_value=400),
    terminal=st.sampled_from([0.0, -2.0]),
    proxy=st.booleans(),
)
def test_exact_nonzero_terminal_discount_below_half_minimum_float_refuses(
    base_exponent: int, discount_exponent: int, terminal: float, proxy: bool
) -> None:
    base = math.ldexp(1.0, base_exponent)
    discount = math.ldexp(1.0, discount_exponent)
    projected = base * (1 - discount) ** 2
    terminal_value = projected * (1 + terminal) / (discount - terminal)
    factor = (1 + discount) ** 2
    # Exact proof concerns reached native operands; no universal cancellation claim.
    assert terminal_value != 0.0 and math.isfinite(factor)
    exact = Fraction(terminal_value) / Fraction(factor)
    assert 0 < abs(exact) < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(
            _history(base=base, proxy=proxy),
            _settings(discount=discount, terminal=terminal),
        )
