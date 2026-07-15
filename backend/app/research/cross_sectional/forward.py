"""Forward-testing for cross-sectional graduates (ADR-025).

A cross-sectional graduate is a whole dollar-neutral long/short PORTFOLIO, not one symbol, so it is
forward-tested by continuing to compute its engine `portfolio_returns` on bars AFTER its freeze
boundary and benchmarking against the equal-weight long-only universe -- the same benchmark ADR-024
used at the holdout. This mirrors the SHAPE of the single-name `paper.py` / `portfolio_manager.py`
(ADR-019/020) at the portfolio level, reusing the ADR-024 engine + registry unchanged. Pure over
injectable panels -- no network, no look-ahead (weights at t use prices <= t).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.backtesting.metrics import sharpe_ratio
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.registry import default_strategies


class CrossSectionalForwardEquityPoint(BaseModel):
    """One bar of the forward equity curve (ADR-023 analog): normalized indices (base 1.0 at the
    freeze boundary) that compound each post-freeze bar -- the factor vs the equal-weight benchmark."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    strategy_equity: float
    benchmark_equity: float


class CrossSectionalForwardScore(BaseModel):
    """A frozen cross-sectional graduate's out-of-sample track record (ADR-025), scored ONLY on bars
    after its freeze date. `benchmark_*` is the equal-weight long-only universe (ADR-024's holdout
    benchmark); `beats_benchmark` is the honest bar: did the dollar-neutral factor out-earn holding
    the whole universe, risk-adjusted, going forward?"""

    model_config = ConfigDict(frozen=True)

    forward_bars: int
    forward_return: float
    forward_sharpe: float
    benchmark_return: float
    benchmark_sharpe: float
    beats_benchmark: bool
    as_of: datetime
    forward_equity: list[CrossSectionalForwardEquityPoint] = []


class CrossSectionalPosition(BaseModel):
    """A cross-sectional graduate frozen for forward-testing (ADR-025). Its config -- the strategy,
    the searched signal params AND quantile, the universe, the cost rate, and (for xs_value) the
    static value-score snapshot -- is locked as of `frozen_at`; everything after is genuinely unseen.
    `score` is the latest forward evaluation (None until first run). A factor is managed: retired when
    it deteriorates, kept afterward as an honest record and never re-promoted."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    parameters: dict[str, float | int]
    universe_symbols: list[str]
    cost_rate: float
    frozen_at: datetime
    value_scores: dict[str, float] | None = None
    score: CrossSectionalForwardScore | None = None
    status: Literal["open", "retired"] = "open"
    retired_at: datetime | None = None
    exit_reasons: list[str] = []


PanelProvider = Callable[[CrossSectionalPosition], pd.DataFrame]


def _factor_returns(position: CrossSectionalPosition, panel: pd.DataFrame) -> pd.Series:
    """Recompute the frozen factor's portfolio return series over the FULL panel by rebuilding its
    signal from the unmodified registry. Warmup happens on the full panel; callers slice the
    post-freeze bars. Reuses `engine.portfolio_returns` -- no reinvented returns math."""
    registry = default_strategies(value_scores=position.value_scores)
    strategy = registry.get(position.strategy_name)
    if strategy is None:
        raise ValueError(f"unknown cross-sectional strategy {position.strategy_name!r}")
    params = {k: v for k, v in position.parameters.items() if k != "quantile"}
    quantile = float(position.parameters["quantile"])
    signal = strategy.build(params)(panel)
    return portfolio_returns(signal, panel, quantile=quantile, cost_rate=position.cost_rate)


def _benchmark_returns(panel: pd.DataFrame) -> pd.Series:
    """The equal-weight long-only universe return (ADR-024's holdout benchmark)."""
    return asset_returns(panel).mean(axis=1)


def score_forward(
    position: CrossSectionalPosition, panel: pd.DataFrame
) -> CrossSectionalForwardScore:
    """Score `position` on the bars of `panel` strictly after its freeze date, vs the equal-weight
    long-only universe (ADR-025). The engine runs over the FULL panel so signals are warmed up by the
    freeze date; only the post-freeze slice is scored. No look-ahead; returns a zero-bar score when no
    forward data has accrued yet."""
    as_of = pd.Timestamp(panel.index.max())
    forward_mask = panel.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return CrossSectionalForwardScore(
            forward_bars=0,
            forward_return=0.0,
            forward_sharpe=0.0,
            benchmark_return=0.0,
            benchmark_sharpe=0.0,
            beats_benchmark=False,
            as_of=as_of.to_pydatetime(),
        )

    fwd = _factor_returns(position, panel)[forward_mask]
    bench = _benchmark_returns(panel)[forward_mask]
    fwd_sharpe = sharpe_ratio(fwd)
    bench_sharpe = sharpe_ratio(bench)
    strat_equity = (1.0 + fwd).cumprod()
    bench_equity = (1.0 + bench).cumprod()
    forward_equity = [
        CrossSectionalForwardEquityPoint(
            timestamp=ts.to_pydatetime(),
            strategy_equity=float(strat_equity.iloc[i]),
            benchmark_equity=float(bench_equity.iloc[i]),
        )
        for i, ts in enumerate(fwd.index)
    ]
    return CrossSectionalForwardScore(
        forward_bars=int(forward_mask.sum()),
        forward_return=float((1.0 + fwd).prod() - 1.0),
        forward_sharpe=fwd_sharpe,
        benchmark_return=float((1.0 + bench).prod() - 1.0),
        benchmark_sharpe=bench_sharpe,
        beats_benchmark=fwd_sharpe > bench_sharpe,
        as_of=as_of.to_pydatetime(),
        forward_equity=forward_equity,
    )
