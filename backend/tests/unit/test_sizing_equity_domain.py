"""Original capital validity at paper sizing, separate from account observations (ADR-340)."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scripts.paper_broker import compute_targets

from app.execution.sizing import PositionQuote, equal_weight_targets


def _quote(signal: float = 1.0, price: float = 100.0) -> PositionQuote:
    return PositionQuote(symbol="TEST", signal=signal, price=price)


@pytest.mark.parametrize(
    "equity",
    [
        -1000.0,
        -0.01,
        -float.fromhex("0x0.0000000000001p-1022"),
        float("nan"),
        float("inf"),
        -float("inf"),
        np.float32(-1000),
        Fraction(-1, 10**400),
        Decimal("-1e-400"),
    ],
)
@pytest.mark.parametrize(
    "quotes",
    [
        [],
        [_quote(0.0)],
        [_quote(price=float("nan"))],
        [_quote(1.0)],
        [_quote(-1.0)],
        [_quote(0.5), _quote(-0.5)],
    ],
)
def test_equal_weight_targets_invalid_equity_refuses_every_layout(
    equity: float, quotes: list[PositionQuote]
) -> None:
    with pytest.raises(ValueError, match="equity must be finite and nonnegative"):
        equal_weight_targets(quotes, equity)


@pytest.mark.parametrize("equity", [0.0, -0.0, np.float32(-0.0), Fraction(0)])
def test_equal_weight_targets_zero_equity_preserves_flat_targets(equity: float) -> None:
    targets = equal_weight_targets([_quote(1.0), _quote(-0.5), _quote(price=float("nan"))], equity)
    assert [t.target_qty for t in targets] == [0, 0, 0]
    assert equal_weight_targets([], equity) == []


@pytest.mark.parametrize("equity", ["1000", None, complex(1000, 0)])
def test_equal_weight_targets_native_inspection_type_error_before_empty_shortcut(
    equity: float,
) -> None:
    with pytest.raises(TypeError):
        equal_weight_targets([], equity)


def test_equal_weight_targets_native_inspection_overflow_before_empty_shortcut() -> None:
    with pytest.raises(OverflowError):
        equal_weight_targets([], 10**400)


def test_equal_weight_targets_finite_decimal_keeps_native_arithmetic_error() -> None:
    assert equal_weight_targets([], Decimal(1000)) == []
    with pytest.raises(TypeError):
        equal_weight_targets([_quote()], Decimal(1000))


@pytest.mark.parametrize("equity", [-1000.0, float("nan"), float("inf"), -float("inf")])
def test_compute_targets_empty_book_propagates_invalid_equity(equity: float) -> None:
    def forbidden_provider(symbol: str) -> None:
        pytest.fail(f"empty book must not acquire {symbol}")

    with pytest.raises(ValueError, match="equity must be finite and nonnegative"):
        compute_targets([], forbidden_provider, equity)


@given(magnitude=st.floats(min_value=1e-300, max_value=1e12, allow_nan=False))
def test_equal_weight_targets_negative_equity_never_reverses_direction(magnitude: float) -> None:
    with pytest.raises(ValueError, match="equity must be finite and nonnegative"):
        equal_weight_targets([_quote(1.0), _quote(-1.0)], -magnitude)


@given(
    equity=st.floats(min_value=0, max_value=1e9, allow_nan=False),
    signal=st.floats(min_value=-1, max_value=1, allow_nan=False),
    price=st.floats(min_value=0.01, max_value=1e6, allow_nan=False),
)
def test_equal_weight_targets_valid_capital_preserves_direction_and_budget(
    equity: float, signal: float, price: float
) -> None:
    qty = equal_weight_targets([_quote(signal, price)], equity)[0].target_qty
    assert qty == 0 or (qty > 0) == (signal > 0)
    # Exact represented share quotient bounds truncation without a rounded notional product.
    assert Fraction(abs(qty)) <= Fraction(abs(equity * signal / price))


def test_equal_weight_targets_nan_price_still_frees_slice() -> None:
    targets = equal_weight_targets([_quote(), _quote(price=float("nan"))], 1000.0)
    assert [t.target_qty for t in targets] == [10, 0]
