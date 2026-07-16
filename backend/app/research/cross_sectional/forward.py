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

from app.research.backtesting.metrics import max_drawdown, sharpe_ratio
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.search import CrossSectionalExperiment


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


class CrossSectionalExitPolicy(BaseModel):
    """Tunable, versioned exit rules for a forward-tested cross-sectional factor (ADR-025) — the
    portfolio-level analog of the single-name ExitPolicy (ADR-020). A grace period avoids cutting on
    entry noise; a rolling trailing window measures RECENT decay so it isn't masked by early gains."""

    model_config = ConfigDict(frozen=True)

    min_forward_bars_before_exit: int = 21  # ~1mo grace
    rolling_window_bars: int = 63  # ~3mo trailing window
    min_rolling_sharpe: float = 0.0
    max_forward_drawdown: float = 0.30
    require_beat_benchmark_forward: bool = True


class CrossSectionalLifecycleDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: Literal["hold", "retire"]
    rolling_sharpe: float
    forward_drawdown: float
    rolling_benchmark_sharpe: float
    reasons: list[str] = []


def lifecycle_from_forward_returns(
    forward_returns: pd.Series,
    benchmark_returns: pd.Series,
    policy: CrossSectionalExitPolicy,
) -> CrossSectionalLifecycleDecision:
    """Decide hold/retire from a factor's FORWARD returns vs the equal-weight benchmark (ADR-025).
    Retire when recent (rolling-window) risk-adjusted performance decays below the floor, the forward
    drawdown breaches the risk limit, or it stops beating the benchmark. Pure -- no engine/network."""
    n = len(forward_returns)
    if n < policy.min_forward_bars_before_exit:
        return CrossSectionalLifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_benchmark_sharpe=0.0,
            reasons=["grace period (insufficient forward data)"],
        )
    equity = (1.0 + forward_returns).cumprod()
    forward_drawdown = abs(max_drawdown(equity))
    roll = forward_returns.iloc[-policy.rolling_window_bars :]
    roll_bench = benchmark_returns.iloc[-policy.rolling_window_bars :]
    rolling_sharpe = sharpe_ratio(roll)
    rolling_bench_sharpe = sharpe_ratio(roll_bench)

    reasons: list[str] = []
    if rolling_sharpe <= policy.min_rolling_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= {policy.min_rolling_sharpe} (edge has decayed)"
        )
    if forward_drawdown > policy.max_forward_drawdown:
        reasons.append(
            f"forward drawdown {forward_drawdown:.1%} > {policy.max_forward_drawdown:.0%} "
            "(risk limit)"
        )
    if policy.require_beat_benchmark_forward and rolling_sharpe <= rolling_bench_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= equal-weight benchmark {rolling_bench_sharpe:.2f}"
            " (no longer beats holding the universe)"
        )
    return CrossSectionalLifecycleDecision(
        action="retire" if reasons else "hold",
        rolling_sharpe=rolling_sharpe,
        forward_drawdown=forward_drawdown,
        rolling_benchmark_sharpe=rolling_bench_sharpe,
        reasons=reasons,
    )


def evaluate_cross_sectional_lifecycle(
    position: CrossSectionalPosition, panel: pd.DataFrame, policy: CrossSectionalExitPolicy
) -> CrossSectionalLifecycleDecision:
    """Recompute the frozen factor's post-freeze forward returns + the equal-weight benchmark on
    `panel` and decide hold/retire (ADR-025). Holds during the grace period / before any forward
    data has accrued."""
    forward_mask = panel.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return CrossSectionalLifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_benchmark_sharpe=0.0,
            reasons=["grace period (no forward data)"],
        )
    fwd = _factor_returns(position, panel)[forward_mask]
    bench = _benchmark_returns(panel)[forward_mask]
    return lifecycle_from_forward_returns(fwd, bench, policy)


def freeze_cross_sectional_graduate(
    experiment: CrossSectionalExperiment,
    frozen_at: datetime,
    *,
    cost_rate: float = 0.001,
    value_scores: dict[str, float] | None = None,
) -> CrossSectionalPosition:
    """Freeze a cross-sectional graduate for forward-testing: lock its strategy, searched params +
    quantile, universe, cost rate, and (for xs_value) the static score snapshot as of `frozen_at`."""
    graduate = experiment.graduate
    if graduate is None:
        raise ValueError("experiment has no graduate to freeze")
    return CrossSectionalPosition(
        strategy_name=graduate.strategy_name,
        parameters=graduate.parameters,
        universe_symbols=experiment.universe_symbols,
        cost_rate=cost_rate,
        frozen_at=frozen_at,
        value_scores=value_scores,
    )


def manage_cross_sectional_book(
    positions: list[CrossSectionalPosition],
    graduate_experiments: list[CrossSectionalExperiment],
    panel_provider: PanelProvider,
    *,
    exit_policy: CrossSectionalExitPolicy | None = None,
    now: datetime,
    cost_rate: float = 0.001,
    value_scores: dict[str, float] | None = None,
) -> list[CrossSectionalPosition]:
    """Advance the cross-sectional forward book one step (ADR-025, mirrors portfolio_manager): PROMOTE
    new graduates (freeze any factor -- (strategy, universe) -- not already tracked), MONITOR every
    OPEN position and RETIRE the deteriorating ones. Retired factors are kept as an honest record and
    never re-promoted. Pure over `panel_provider` -> testable without network."""
    policy = exit_policy or CrossSectionalExitPolicy()

    held = {(p.strategy_name, tuple(sorted(p.universe_symbols))) for p in positions}
    book = list(positions)
    for experiment in graduate_experiments:
        if experiment.graduate is None:
            continue
        key = (experiment.graduate.strategy_name, tuple(sorted(experiment.universe_symbols)))
        if key in held:
            continue
        book.append(
            freeze_cross_sectional_graduate(
                experiment, frozen_at=now, cost_rate=cost_rate, value_scores=value_scores
            )
        )
        held.add(key)

    updated: list[CrossSectionalPosition] = []
    for position in book:
        if position.status != "open":
            updated.append(position)
            continue
        panel = panel_provider(position)
        score = score_forward(position, panel)
        decision = evaluate_cross_sectional_lifecycle(position, panel, policy)
        if decision.action == "retire":
            updated.append(
                position.model_copy(
                    update={
                        "status": "retired",
                        "retired_at": now,
                        "exit_reasons": decision.reasons,
                        "score": score,
                    }
                )
            )
        else:
            updated.append(position.model_copy(update={"score": score}))
    return updated
