"""Sizing for real Alpaca paper execution (ADR-021). Pure math + thin engine wiring: resolve each
OPEN PaperPosition to its latest signal, then equal-weight the book into signed whole-share targets.
No network — the signal path runs the frozen strategy over an injected frame."""

from datetime import UTC, datetime

import pandas as pd
import pytest
from pydantic import ValidationError

from app.execution.sizing import (
    PositionQuote,
    TargetPosition,
    equal_weight_targets,
    latest_signal,
    quote_position,
)
from app.research.lab.paper import PaperPosition


def _uptrend_frame() -> pd.DataFrame:
    # SMA(2,4): trailing fast mean > slow mean at the last bar → long (+1).
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.DataFrame({"close": [1.0, 2, 3, 4, 5, 6, 7, 8]}, index=idx)


def _downtrend_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.DataFrame({"close": [8.0, 7, 6, 5, 4, 3, 2, 1]}, index=idx)


def _position(symbol: str = "AAPL") -> PaperPosition:
    return PaperPosition(
        symbol=symbol,
        strategy_name="sma",
        parameters={"fast": 2, "slow": 4},
        frozen_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


# --- latest_signal / quote_position (engine wiring) ---


def test_latest_signal_uptrend_is_long() -> None:
    assert latest_signal(_position(), _uptrend_frame()) == 1.0


def test_latest_signal_downtrend_is_short() -> None:
    assert latest_signal(_position(), _downtrend_frame()) == -1.0


def test_latest_signal_matches_strategys_last_generated_weight() -> None:
    frame = _uptrend_frame()
    from app.research.strategies.builder import build_strategy_from_dict

    strategy = build_strategy_from_dict("sma", {"fast": 2, "slow": 4})
    expected = float(strategy.generate_signals(frame).iloc[-1])
    assert latest_signal(_position(), frame) == expected


def test_latest_signal_is_clipped_to_unit_interval() -> None:
    sig = latest_signal(_position(), _uptrend_frame())
    assert -1.0 <= sig <= 1.0


def test_quote_position_carries_symbol_signal_and_last_close() -> None:
    quote = quote_position(_position("MSFT"), _uptrend_frame())
    assert quote.symbol == "MSFT"
    assert quote.signal == 1.0
    assert quote.price == 8.0


# --- equal_weight_targets (pure sizing math) ---


def test_equal_weight_splits_equity_across_active_names() -> None:
    quotes = [
        PositionQuote(symbol="AAPL", signal=1.0, price=100.0),
        PositionQuote(symbol="MSFT", signal=1.0, price=50.0),
    ]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    by_symbol = {t.symbol: t.target_qty for t in targets}
    assert by_symbol == {"AAPL": 50, "MSFT": 100}  # 5000 each → 50 and 100 shares


def test_flat_signal_gets_zero_target_and_frees_its_slice() -> None:
    quotes = [
        PositionQuote(symbol="AAPL", signal=1.0, price=100.0),
        PositionQuote(symbol="MSFT", signal=0.0, price=50.0),
    ]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    by_symbol = {t.symbol: t.target_qty for t in targets}
    # Only AAPL is active → it gets the full 10_000 → 100 shares; MSFT flat → 0.
    assert by_symbol == {"AAPL": 100, "MSFT": 0}


def test_short_signal_produces_negative_target() -> None:
    quotes = [PositionQuote(symbol="AAPL", signal=-1.0, price=100.0)]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    assert targets[0].target_qty == -100


def test_fractional_signal_scales_the_slice_by_conviction() -> None:
    quotes = [PositionQuote(symbol="AAPL", signal=0.5, price=100.0)]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    assert targets[0].target_qty == 50  # 10_000 * 0.5 / 100


def test_target_quantity_truncates_toward_zero() -> None:
    quotes = [PositionQuote(symbol="AAPL", signal=1.0, price=300.0)]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    assert targets[0].target_qty == 33  # 33.33 → 33 whole shares


def test_empty_quotes_gives_empty_targets() -> None:
    assert equal_weight_targets([], equity=10_000.0) == []


def test_all_flat_gives_all_zero_targets() -> None:
    quotes = [
        PositionQuote(symbol="AAPL", signal=0.0, price=100.0),
        PositionQuote(symbol="MSFT", signal=0.0, price=50.0),
    ]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    assert all(t.target_qty == 0 for t in targets)


def test_nonpositive_price_is_treated_as_flat() -> None:
    quotes = [PositionQuote(symbol="AAPL", signal=1.0, price=0.0)]
    targets = equal_weight_targets(quotes, equity=10_000.0)
    assert targets[0].target_qty == 0


def test_position_quote_and_target_are_frozen() -> None:
    q = PositionQuote(symbol="AAPL", signal=1.0, price=100.0)
    t = TargetPosition(symbol="AAPL", target_qty=50)
    with pytest.raises(ValidationError):
        q.signal = 0.0  # type: ignore[misc]
    with pytest.raises(ValidationError):
        t.target_qty = 0  # type: ignore[misc]
