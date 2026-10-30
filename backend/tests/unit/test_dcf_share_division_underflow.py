"""ADR-409: final DCF division cannot erase a nonzero equity numerator."""

import math
import sys
from datetime import date
from fractions import Fraction
from typing import NoReturn

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation.intrinsic_value import DcfAssumptions, dcf_intrinsic_value
from app.research.valuation.score import score_valuation

_ERROR = "^intrinsic_value_per_share must not underflow to zero for DCF$"
_FLAT = DcfAssumptions(terminal_growth=0.0, min_growth=0.0, max_growth=0.0)
_NEGATIVE = DcfAssumptions(
    terminal_growth=0.0, min_growth=-2.0, max_growth=-2.0, projection_years=1
)
_ZERO = DcfAssumptions(terminal_growth=0.0, min_growth=-1.0, max_growth=-1.0)


def _history(
    *, base: float = 1e-300, shares: float = 1e300, proxy: bool = False, count: int = 2
) -> FundamentalsHistory:
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
                revenue=1e308,
                net_income=base if proxy else 1.0,
                eps=1.0,
                free_cash_flow=None if proxy else base,
                shares_diluted=shares,
                price=10.0,
            )
            for i in range(count)
        ),
    )


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("assumptions", [_FLAT, _NEGATIVE])
def test_nonzero_dcf_division_refuses_signed_zero(
    count: int, proxy: bool, assumptions: DcfAssumptions
) -> None:
    # Flat perpetuity / one-step negative-growth examples are nonzero and tiny.
    exact_magnitude = Fraction(1e-300) / Fraction(0.1) / Fraction(1e300)
    assert 0 < exact_magnitude < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(_history(proxy=proxy, count=count), assumptions)


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("assumptions", [_FLAT, _NEGATIVE])
def test_composite_refuses_final_division_loss_instead_of_absent_margin(
    count: int, proxy: bool, assumptions: DcfAssumptions
) -> None:
    with pytest.raises(ValueError, match=_ERROR):
        score_valuation(_history(proxy=proxy, count=count), 1.0, assumptions=assumptions)


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
def test_record_refuses_final_dcf_division_loss(count: int, proxy: bool) -> None:
    with pytest.raises(ValueError, match=_ERROR):
        compute_fundamental_record(_history(proxy=proxy, count=count), 1.0)


@pytest.mark.parametrize("proxy", [False, True])
def test_injected_value_provider_propagates_division_refusal(proxy: bool) -> None:
    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
    )
    with pytest.raises(ValueError, match=_ERROR):
        provider("SYN")


@pytest.mark.parametrize("config", [None, ValueGateConfig()])
@pytest.mark.parametrize("proxy", [False, True])
def test_hunt_records_division_error_before_frame_acquisition(
    config: ValueGateConfig | None, proxy: bool
) -> None:
    calls: list[str] = []

    def acquire(symbol: str) -> NoReturn:
        calls.append(symbol)
        raise AssertionError("must not acquire after invalid valuation")

    provider = make_value_provider(
        lambda _: _history(proxy=proxy),
        lambda _: [(date(2023, 12, 31), 10.0), (date(2024, 12, 31), 1.0)],
    )
    result = run_universe_hunt(
        ["SYN"], ["sma"], acquire, value_provider=provider, value_config=config
    )
    assert calls == []
    assert result.experiments == []
    assert result.filtered == {}
    assert result.errors == {
        "SYN": "ValueError: intrinsic_value_per_share must not underflow to zero for DCF"
    }


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("proxy", [False, True])
def test_genuine_zero_equity_retains_zero_and_existing_composite_policy(
    count: int, proxy: bool
) -> None:
    history = _history(proxy=proxy, count=count)
    result = dcf_intrinsic_value(history, _ZERO)
    assert result.intrinsic_value_per_share == 0.0
    valuation = score_valuation(history, 1.0, assumptions=_ZERO)
    assert valuation.intrinsic_value_per_share == 0.0
    assert valuation.margin_of_safety is None
    assert valuation.score == (None if count == 1 else 1.0)


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("assumptions,sign", [(_FLAT, 1.0), (_NEGATIVE, -1.0)])
def test_nonzero_subnormal_dcf_quotient_retains_native_value(
    proxy: bool, assumptions: DcfAssumptions, sign: float
) -> None:
    result = dcf_intrinsic_value(_history(proxy=proxy, shares=1e24), assumptions)
    value = result.intrinsic_value_per_share
    assert value is not None and 0.0 < abs(value) < sys.float_info.min
    assert math.copysign(1.0, value) == sign
    assert value == sign * float.fromhex("0x0.0000000000002p-1022")


@given(
    base_exponent=st.integers(min_value=-1000, max_value=-700),
    share_exponent=st.integers(min_value=700, max_value=1000),
    proxy=st.booleans(),
)
def test_nonzero_perpetuity_below_half_minimum_float_refuses(
    base_exponent: int, share_exponent: int, proxy: bool
) -> None:
    base, shares = math.ldexp(1.0, base_exponent), math.ldexp(1.0, share_exponent)
    exact = Fraction(base) / Fraction(_FLAT.discount_rate) / Fraction(shares)
    assert 0 < exact < Fraction(math.ulp(0.0)) / 2
    with pytest.raises(ValueError, match=_ERROR):
        dcf_intrinsic_value(_history(base=base, shares=shares, proxy=proxy), _FLAT)
