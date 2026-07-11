"""Wire the ADR-023 value engine into the universe-hunt scripts (WP-J), RECORD-FIRST.

The hunt already fetches a daily price frame per symbol; this module reuses that frame to build the
`(date, close)` series the valuation `price_join` needs, so composing an `UndervaluationScore` costs
no extra price fetch. Combined with an EDGAR fundamentals-history source it yields an injectable
`ValueProvider` that RECORDS a cited score on every candidate. Recording is on by default; the hard
`ValueGateConfig` is opt-in via `--value-screen` (calibrate the min_score before enforcing).

Resilient by construction (the 503-name EDGAR/price sweep gotcha): a per-symbol history OR frame
failure yields None -> that name is hunted on technicals only, never crashing the run.
"""

from collections.abc import Callable, Sequence
from datetime import date

import pandas as pd

from app.research.lab.value_filter import (
    HistoryProvider,
    ValueGateConfig,
    ValueProvider,
    make_value_provider,
)
from app.research.valuation.intrinsic_value import DcfAssumptions

FrameProvider = Callable[[str], pd.DataFrame]

_VALUE_SCREEN_FLAG = "--value-screen"


def frame_to_close_series(frame: pd.DataFrame) -> list[tuple[date, float]]:
    """Extract the ascending ``(date, close)`` series a `price_join` needs from a research price
    frame. Empty frame -> empty series (the provider then yields None -> technicals only)."""
    if frame.empty:
        return []
    return [
        (ts.date(), float(close)) for ts, close in zip(frame.index, frame["close"], strict=True)
    ]


def cached_frame_provider(frame_provider: FrameProvider) -> FrameProvider:
    """Memoize ``frame_provider`` per symbol so the hunt's backtest fetch and the value price series
    share ONE fetch — the 503-name sweep must not double the price load."""
    cache: dict[str, pd.DataFrame] = {}

    def provide(symbol: str) -> pd.DataFrame:
        if symbol not in cache:
            cache[symbol] = frame_provider(symbol)
        return cache[symbol]

    return provide


def make_hunt_value_provider(
    history_provider: HistoryProvider,
    frame_provider: FrameProvider,
    *,
    assumptions: DcfAssumptions | None = None,
) -> ValueProvider:
    """Compose an EDGAR fundamentals-history source + the hunt's own price frame into a per-symbol
    `UndervaluationScore` provider (RECORD-FIRST). A frame the provider cannot fetch (ETF / no data)
    yields no closes -> None -> that name is hunted on technicals only. Both inputs are injected, so
    CI uses fakes and a `@pytest.mark.live` test wires real EDGAR + real bars."""

    def price_series_provider(symbol: str) -> list[tuple[date, float]]:
        try:
            frame = frame_provider(symbol)
        except (ValueError, KeyError, OSError):
            return []
        return frame_to_close_series(frame)

    return make_value_provider(history_provider, price_series_provider, assumptions=assumptions)


def parse_value_screen(args: Sequence[str]) -> tuple[ValueGateConfig | None, list[str]]:
    """Parse an optional ``--value-screen [MIN_SCORE]`` flag out of CLI args (WP-J).

    Absent -> value RECORDING only (config None: the hard gate is off). Present -> the hard
    `ValueGateConfig` gate; a following float overrides ``min_score``, otherwise the permissive
    default (0.5, still needs calibration). Returns the config and the remaining args (symbols or a
    universe .txt path). A non-float token after the flag is treated as a symbol, not a min_score.
    """
    config: ValueGateConfig | None = None
    rest: list[str] = []
    tokens = list(args)
    i = 0
    while i < len(tokens):
        if tokens[i] != _VALUE_SCREEN_FLAG:
            rest.append(tokens[i])
            i += 1
            continue
        min_score: float | None = None
        if i + 1 < len(tokens):
            try:
                min_score = float(tokens[i + 1])
            except ValueError:
                min_score = None
            else:
                i += 1  # consume the numeric override
        config = ValueGateConfig() if min_score is None else ValueGateConfig(min_score=min_score)
        i += 1
    return config, rest
