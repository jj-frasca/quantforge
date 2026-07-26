from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd

from app.research.cross_sectional.search import (
    CrossSectionalExperiment,
    run_cross_sectional_search,
)
from app.research.cross_sectional.store import CrossSectionalExperimentStore
from app.research.lab.gate import GateConfig

FrameProvider = Callable[[str], pd.DataFrame]

_MIN_SYMBOLS = 2
# A symbol needs at least this many bars to join the panel; the cross-sectional split needs
# search (>=252) + holdout (>=252). Dropping short-history names (recent IPOs, truncated vendor
# responses) stops ONE 28-bar symbol from collapsing the whole dropna intersection (prod 2026-07-26).
_MIN_HISTORY_BARS = 504


@dataclass(frozen=True)
class CrossSectionalHuntResult:
    experiment: CrossSectionalExperiment
    panel_bars: int
    errors: dict[str, str] = field(default_factory=dict)


def price_panel_from_frames(
    frames: Mapping[str, pd.DataFrame], *, min_bars: int = _MIN_HISTORY_BARS
) -> pd.DataFrame:
    """Align per-symbol price frames into one (dates x symbols) close panel. Symbols with fewer than
    `min_bars` observations are dropped FIRST, then columns are joined on the union of dates and rows
    with any missing symbol removed, so the panel is a rectangular block over the survivors' common,
    gap-free date range — exactly what the ranker needs to compare like-for-like each period.

    Dropping short-history symbols is load-bearing: a single recent-IPO / truncated-vendor symbol
    with only a handful of bars would otherwise collapse the dropna intersection to those few dates
    and starve the search (prod 2026-07-26). Long-history names keep their full common window."""
    closes = {
        symbol: frame["close"]
        for symbol, frame in frames.items()
        if int(frame["close"].notna().sum()) >= min_bars
    }
    panel = pd.DataFrame(closes)
    return panel.dropna()


def run_cross_sectional_hunt(
    symbols: Sequence[str],
    frame_provider: FrameProvider,
    *,
    store: CrossSectionalExperimentStore,
    strategy_names: Sequence[str] | None = None,
    value_scores: Mapping[str, float] | None = None,
    quantiles: Sequence[float] = (0.1, 0.2, 0.3),
    config: GateConfig | None = None,
    cost_rate: float = 0.001,
    rationale: str = "",
) -> CrossSectionalHuntResult:
    """Run one cross-sectional hunt over a symbol universe (ADR-024 integration). Fetch each
    symbol's frame resiliently (a per-symbol failure is recorded and skipped), assemble the price
    panel, run the search with the pool's cumulative `prior_trials` (so search effort compounds via
    MinTRL), persist the experiment, and return it with the panel/skip metadata. Pure over its
    provider + store → unit-testable without network."""
    frames: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            frames[symbol] = frame_provider(symbol)
        except (ValueError, KeyError, OSError, ArithmeticError, TypeError) as exc:
            # A per-symbol fetch/normalize failure over unreliable vendor data must NOT kill the
            # whole universe hunt — record it and move on. ArithmeticError covers the OHLCV
            # normalizer's decimal.InvalidOperation on a malformed (NaN) bar (prod 2026-07-26).
            errors[symbol] = f"{type(exc).__name__}: {exc}"

    panel = price_panel_from_frames(frames)
    if panel.shape[1] < _MIN_SYMBOLS:
        raise ValueError(
            f"need at least {_MIN_SYMBOLS} symbols with data to rank cross-sectionally, "
            f"got {panel.shape[1]}"
        )

    experiment = run_cross_sectional_search(
        panel,
        strategy_names,
        value_scores=value_scores,
        quantiles=quantiles,
        config=config,
        prior_trials=store.prior_trials(),
        cost_rate=cost_rate,
        rationale=rationale,
    )
    store.add(experiment)
    return CrossSectionalHuntResult(experiment=experiment, panel_bars=len(panel), errors=errors)
