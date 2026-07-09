"""Position sizing for real Alpaca paper execution (ADR-021).

Resolve each OPEN ``PaperPosition`` to its latest signal (the frozen strategy's position weight on
the most recent bar, in [-1, 1]), then equal-weight the book into signed whole-share targets. The
signal path runs the engine over an injected frame, so it is deterministic and network-free.
"""

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.lab.paper import PaperPosition
from app.research.strategies.builder import build_strategy_from_dict


class PositionQuote(BaseModel):
    """An OPEN position resolved to what execution needs: its latest signal and current price."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    signal: float  # latest position weight in [-1, 1] (sign = direction, magnitude = conviction)
    price: float


class TargetPosition(BaseModel):
    """A desired holding in whole shares. Signed: negative = short, 0 = flat."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    target_qty: int


def latest_signal(position: PaperPosition, frame: pd.DataFrame) -> float:
    """The frozen strategy's position weight on the last bar of ``frame`` (clipped to [-1, 1])."""
    strategy = build_strategy_from_dict(position.strategy_name, position.parameters)
    signals = strategy.generate_signals(frame)
    return float(min(1.0, max(-1.0, float(signals.iloc[-1]))))


def quote_position(position: PaperPosition, frame: pd.DataFrame) -> PositionQuote:
    """Resolve a position to its latest signal + last close."""
    return PositionQuote(
        symbol=position.symbol,
        signal=latest_signal(position, frame),
        price=float(frame["close"].iloc[-1]),
    )


def equal_weight_targets(quotes: list[PositionQuote], equity: float) -> list[TargetPosition]:
    """Split ``equity`` equally across names with a non-zero signal; each name's dollar target is
    its slice scaled by its signal (signed), truncated to whole shares toward zero.

    Notes:
        A flat name (signal 0) or a non-positive price yields a 0 target and frees its slice for the
        active names. Whole-share sizing keeps the reconcile diff a clean integer (idempotent).
    """
    active = sum(1 for q in quotes if q.signal != 0.0 and q.price > 0.0)
    targets: list[TargetPosition] = []
    for q in quotes:
        if active == 0 or q.signal == 0.0 or q.price <= 0.0:
            targets.append(TargetPosition(symbol=q.symbol, target_qty=0))
            continue
        target_dollars = (equity / active) * q.signal
        targets.append(TargetPosition(symbol=q.symbol, target_qty=int(target_dollars / q.price)))
    return targets
