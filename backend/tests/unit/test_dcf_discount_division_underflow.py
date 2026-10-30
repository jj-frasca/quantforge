"""ADR-410: finite native period discounting cannot erase nonzero flow."""

import math
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

_ERROR = "^discounted_cash_flow must not underflow to zero for DCF year 1$"


def _settings(
    *, negative: bool = False, discount: float = 1e300, horizon: int = 1
) -> DcfAssumptions:
    growth = -2.0 if negative else 0.0
    return DcfAssumptions(
        discount_rate=discount,
        terminal_growth=0.0,
        min_growth=growth,
        max_growth=growth,
        projection_years=horizon,
    )


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
                fiscal_year=2025 - count + i,
                period_end=date(2025 - count + i, 12, 31),
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


def _score(history: FundamentalsHistory, assumptions: DcfAssumptions) -> object:
    return score_valuation(history, 1.0, assumptions=assumptions)


@pytest.mark.parametrize("consume", [dcf_intrinsic_value, _score])
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("negative", [False, True])
def test_nonzero_period_flow_refuses_zero_finite_discount_quotient(
    consume: Callable[[FundamentalsHistory, DcfAssumptions], object],
    count: int,
    proxy: bool,
    negative: bool,
) -> None:
    # The first projected flow is exactly +/- base; native factor (1+r)**1 is finite.
    magnitude = Fraction(1e-300) / Fraction(1.0 + 1e300)
    assert 0 < magnitude < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        consume(_history(proxy=proxy, count=count), _settings(negative=negative))


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("negative", [False, True])
def test_custom_value_provider_propagates_period_discount_refusal(
    proxy: bool, negative: bool
) -> None:
    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
        assumptions=_settings(negative=negative),
    )
    with pytest.raises(ValueError, match=_ERROR):
        provider("SYN")


@pytest.mark.parametrize("config", [None, ValueGateConfig()])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("negative", [False, True])
def test_custom_hunt_refusal_precedes_downstream_frame_acquisition(
    config: ValueGateConfig | None, proxy: bool, negative: bool
) -> None:
    calls: list[str] = []

    def acquire(symbol: str) -> NoReturn:
        calls.append(symbol)
        raise AssertionError("must not acquire after invalid period discount")

    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
        assumptions=_settings(negative=negative),
    )
    result = run_universe_hunt(
        ["SYN"], ["sma"], acquire, value_provider=provider, value_config=config
    )
    assert calls == []
    assert result.experiments == [] and result.filtered == {}
    assert result.errors == {
        "SYN": "ValueError: discounted_cash_flow must not underflow to zero for DCF year 1"
    }


@pytest.mark.parametrize("discount", [1e200, 1e300])
def test_earlier_period_loss_now_precedes_later_power_overflow(discount: float) -> None:
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(_history(), _settings(discount=discount, horizon=2))


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
def test_genuine_zero_projected_flow_preserves_native_zero(count: int, proxy: bool) -> None:
    assumptions = _settings().model_copy(update={"min_growth": -1.0, "max_growth": -1.0})
    history = _history(proxy=proxy, count=count)
    assert dcf_intrinsic_value(history, assumptions).intrinsic_value_per_share == 0.0
    valuation = score_valuation(history, 1.0, assumptions=assumptions)
    assert valuation.margin_of_safety is None
    assert valuation.score == (None if count == 1 else 1.0)


@pytest.mark.parametrize("negative", [False, True])
def test_nonzero_subnormal_period_flow_refuses_lost_terminal_discount(negative: bool) -> None:
    # ADR-412 retains these original inputs and refuses their lost terminal term.
    with pytest.raises(
        ValueError, match=r"^discounted_terminal_value must not underflow to zero for DCF$"
    ):
        dcf_intrinsic_value(_history(), _settings(discount=1e23, negative=negative))


@pytest.mark.parametrize("horizon", [0, -1])
def test_terminal_only_zero_loss_now_refuses_at_terminal_guard(horizon: int) -> None:
    # ADR-411 supersedes terminal-only loss acceptance; retain both original horizons.
    with pytest.raises(ValueError, match=r"^terminal_value must not underflow to zero for DCF$"):
        dcf_intrinsic_value(_history(), _settings(horizon=horizon))


def test_unchecked_infinite_factor_keeps_existing_direct_and_metadata_policy() -> None:
    assumptions = _settings().model_copy(update={"discount_rate": math.inf})
    assert dcf_intrinsic_value(_history(), assumptions).intrinsic_value_per_share == 0.0
    with pytest.raises(ValueError, match="finite"):
        score_valuation(_history(), 1.0, assumptions=assumptions)


def test_native_power_failure_before_reached_guard_still_propagates() -> None:
    with pytest.raises(OverflowError):
        dcf_intrinsic_value(_history(base=1e300), _settings(discount=1e200, horizon=2))


def test_native_zero_discount_factor_still_raises_division_error() -> None:
    assumptions = DcfAssumptions(
        discount_rate=-1.0,
        terminal_growth=-2.0,
        min_growth=0.0,
        max_growth=0.0,
        projection_years=1,
    )
    with pytest.raises(ZeroDivisionError):
        dcf_intrinsic_value(_history(), assumptions)


@given(
    base_exponent=st.integers(min_value=-1000, max_value=-700),
    discount_exponent=st.integers(min_value=700, max_value=1000),
    proxy=st.booleans(),
)
def test_exact_nonzero_period_quotient_below_half_minimum_float_refuses(
    base_exponent: int, discount_exponent: int, proxy: bool
) -> None:
    base = math.ldexp(1.0, base_exponent)
    discount = math.ldexp(1.0, discount_exponent)
    exact = Fraction(base) / Fraction(1.0 + discount)
    assert 0 < exact < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(_history(base=base, proxy=proxy), _settings(discount=discount))
