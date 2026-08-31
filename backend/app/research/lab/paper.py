import json
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.manifest import compute_parameter_hash
from app.research.backtesting.metrics import max_drawdown, sharpe_ratio
from app.research.lab.experiment import Experiment
from app.research.lab.universe import expected_max_sharpe_under_null
from app.research.strategies.builder import build_strategy_from_dict

_TRADING_DAYS = 252


class ForwardEquityPoint(BaseModel):
    """One bar of the forward equity curve (ADR-023): a normalized index (base 1.0 at the freeze
    boundary) that compounds each post-freeze bar. Floats — a derived stat, not a price."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    strategy_equity: float
    buy_and_hold_equity: float


class ForwardScore(BaseModel):
    """A frozen strategy's out-of-time performance (ADR-019), scored ONLY on bars after the freeze
    date — data it could not have been fit to. `beats_buy_and_hold` is the honest bar: did the
    strategy earn more than simply holding the name, risk-adjusted, going forward?

    Notes: `forward_equity` (ADR-023) is the per-bar equity index for the dashboard curve; it is
    additive + defaulted so scores persisted before ADR-023 still validate (they carry an empty
    series until the next accrual repopulates them)."""

    model_config = ConfigDict(frozen=True)

    forward_bars: int
    forward_return: float
    forward_sharpe: float
    buy_and_hold_return: float
    buy_and_hold_sharpe: float
    beats_buy_and_hold: bool
    as_of: datetime
    forward_equity: list[ForwardEquityPoint] = []
    # ADR-073. Defaulted so scores persisted before it still validate; a stored 0 on an old score
    # is indistinguishable from "never traded", which is the honest reading of a zero-return series.
    forward_trades: int = 0


class PaperPosition(BaseModel):
    """A graduate frozen for forward-testing: its config is locked as of `frozen_at`; everything
    after is genuinely unseen. `score` is the latest forward evaluation (None until first run)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    parameters: dict[str, float | int]
    frozen_at: datetime
    score: ForwardScore | None = None
    # Lifecycle (ADR-020): a position is managed — closed automatically when it deteriorates.
    status: Literal["open", "closed"] = "open"
    closed_at: datetime | None = None
    exit_reasons: list[str] = []
    # ADR-033: the cross-symbol-selection verdict AS OF PROMOTION. Recorded, never recomputed — the
    # bar depends on the universe size at the moment of selection, so back-computing today's N would
    # rewrite the test this position actually faced. None = honestly unknown (a single-symbol run,
    # or a position frozen before ADR-033), which is excluded from cohort comparisons, not assumed
    # into one. Recorded and reported; it does NOT block promotion — see ADR-033 on why the
    # non-survivors are the control group.
    survives_universe_deflation: bool | None = None
    universe_deflation_bar: float | None = None
    universe_n_symbols: int | None = None


class ExitPolicy(BaseModel):
    """Tunable, versioned exit rules (ADR-020) — the risk discipline that cuts a decaying strategy.
    Same calibration philosophy as GateConfig (ADR-015)."""

    model_config = ConfigDict(frozen=True)

    min_forward_bars_before_exit: int = 21  # ~1mo grace: don't cut on entry noise
    rolling_window_bars: int = 63  # ~3mo trailing window for "recent" performance
    min_rolling_sharpe: float = 0.0
    max_forward_drawdown: float = 0.25
    require_beat_buy_and_hold_forward: bool = True
    # ADR-073: how long a position that has NEVER traded is held before it is retired as
    # unevaluable. Not a performance bar — the Sharpe rules cannot run on zero trades at all.
    # ASSUMPTION, not a measurement: calibrate against observed time-to-first-trade.
    max_bars_without_trade: int = 126

    @property
    def version_hash(self) -> str:
        return compute_parameter_hash(self.model_dump())


class LifecycleDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: Literal["hold", "exit"]
    rolling_sharpe: float
    forward_drawdown: float
    rolling_buy_and_hold_sharpe: float
    reasons: list[str] = []


def lifecycle_from_returns(
    forward_returns: pd.Series,
    buy_and_hold_returns: pd.Series,
    policy: ExitPolicy,
    n_forward_trades: int,
) -> LifecycleDecision:
    """Decide hold/exit from a position's FORWARD returns (ADR-020). Uses a rolling trailing window
    so recent decay isn't masked by early gains. Pure — no engine/network, fully controllable.

    `n_forward_trades` is required, not inferred (ADR-073): the Sharpe rules below are verdicts on
    a strategy's TRADING, and on zero trades the return series is all zeros, whose Sharpe
    `sharpe_ratio` manufactures as 0.0 for a degenerate series. Applying the rules to that constant
    reads "no evidence" as "failing grade" and cut 18 of the book's 27 closed positions before they
    ever took a position.
    """
    n = len(forward_returns)
    if n < policy.min_forward_bars_before_exit:
        return LifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_buy_and_hold_sharpe=0.0,
            reasons=["grace period (insufficient forward data)"],
        )
    if n_forward_trades == 0:
        # ADR-073: unmeasured, not failed. Retired only for being unevaluable, in wording that
        # cannot be read back as a performance verdict.
        if n >= policy.max_bars_without_trade:
            return LifecycleDecision(
                action="exit",
                rolling_sharpe=0.0,
                forward_drawdown=0.0,
                rolling_buy_and_hold_sharpe=0.0,
                reasons=[
                    f"never traded in {n} forward bars "
                    f"(>= {policy.max_bars_without_trade}; signal too rare to evaluate)"
                ],
            )
        return LifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_buy_and_hold_sharpe=0.0,
            reasons=[f"not yet measurable (0 trades in {n} forward bars)"],
        )
    equity = (1.0 + forward_returns).cumprod()
    forward_drawdown = abs(max_drawdown(equity))
    roll = forward_returns.iloc[-policy.rolling_window_bars :]
    roll_bh = buy_and_hold_returns.iloc[-policy.rolling_window_bars :]
    rolling_sharpe = sharpe_ratio(roll)
    rolling_bh_sharpe = sharpe_ratio(roll_bh)

    reasons: list[str] = []
    if rolling_sharpe <= policy.min_rolling_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= {policy.min_rolling_sharpe} (edge has decayed)"
        )
    if forward_drawdown > policy.max_forward_drawdown:
        reasons.append(
            f"forward drawdown {forward_drawdown:.1%} > {policy.max_forward_drawdown:.0%} (risk limit)"
        )
    if policy.require_beat_buy_and_hold_forward and rolling_sharpe <= rolling_bh_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= buy-and-hold {rolling_bh_sharpe:.2f} "
            "(no longer beats holding the name)"
        )
    return LifecycleDecision(
        action="exit" if reasons else "hold",
        rolling_sharpe=rolling_sharpe,
        forward_drawdown=forward_drawdown,
        rolling_buy_and_hold_sharpe=rolling_bh_sharpe,
        reasons=reasons,
    )


def evaluate_lifecycle(
    position: PaperPosition, frame: pd.DataFrame, policy: ExitPolicy
) -> LifecycleDecision:
    """Run the strategy over `frame` and decide hold/exit on its post-freeze forward slice."""
    forward_mask = frame.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return LifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_buy_and_hold_sharpe=0.0,
            reasons=["no forward data yet"],
        )
    strategy = build_strategy_from_dict(position.strategy_name, position.parameters)
    result = BacktestEngine().run_strategy(frame, strategy)
    fwd = result.returns[forward_mask]
    bh = frame["close"].pct_change().fillna(0.0)[forward_mask]
    return lifecycle_from_returns(fwd, bh, policy, _forward_trades(result.position, forward_mask))


def freeze_graduate(
    experiment: Experiment, frozen_at: datetime, universe_n_symbols: int | None = None
) -> PaperPosition:
    """Turn a graduated Experiment into a paper position frozen as of `frozen_at`.

    `universe_n_symbols` is the number of names this graduate was selected from; given it, the
    ADR-018 best-of-N-under-the-null bar and the verdict against it are recorded on the position
    (ADR-033). Omitted (a single-symbol run) leaves the verdict honestly unknown — there was no
    cross-symbol selection to deflate, which is not the same as passing.
    """
    if experiment.graduate is None:
        raise ValueError(f"experiment for {experiment.symbol!r} has no graduate to freeze")
    g = experiment.graduate
    bar: float | None = None
    survives: bool | None = None
    if universe_n_symbols is not None:
        bar = expected_max_sharpe_under_null(universe_n_symbols, g.holdout_n_bars / _TRADING_DAYS)
        survives = g.holdout_sharpe > bar
    return PaperPosition(
        symbol=experiment.symbol,
        strategy_name=g.strategy_name,
        parameters=g.parameters,
        frozen_at=frozen_at,
        survives_universe_deflation=survives,
        universe_deflation_bar=bar,
        universe_n_symbols=universe_n_symbols,
    )


def _forward_trades(positions: pd.Series, forward_mask: "pd.Series[bool]") -> int:
    """Trades taken inside the forward window, in the engine's own convention (ADR-073).

    Mirrors `BacktestEngine.run_strategy`: turnover is |Δposition| with the first bar charged at
    |position|. Differencing over the FULL series before masking is deliberate — an entry taken on
    the first forward bar is a forward trade, and diffing the slice would hide it.
    """
    turnover = positions.diff().abs().fillna(positions.abs())
    return int((turnover[forward_mask] > 0).sum())


def evaluate_forward(position: PaperPosition, frame: pd.DataFrame) -> ForwardScore:
    """Score `position` on the bars of `frame` strictly after its freeze date.

    The engine runs over the FULL frame so signals are warmed up by the freeze date; only the
    post-freeze slice is scored. Deterministic; no network. Returns a zero-bar score if no forward
    data has accrued yet.
    """
    as_of = pd.Timestamp(frame.index.max())
    forward_mask = frame.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return ForwardScore(
            forward_bars=0,
            forward_return=0.0,
            forward_sharpe=0.0,
            buy_and_hold_return=0.0,
            buy_and_hold_sharpe=0.0,
            beats_buy_and_hold=False,
            as_of=as_of,
            forward_trades=0,
        )

    strategy = build_strategy_from_dict(position.strategy_name, position.parameters)
    result = BacktestEngine().run_strategy(frame, strategy)

    fwd = result.returns[forward_mask]
    bh = frame["close"].pct_change().fillna(0.0)[forward_mask]
    fwd_sharpe = sharpe_ratio(fwd)
    bh_sharpe = sharpe_ratio(bh)
    # Normalized equity indices (base 1.0), compounding each forward bar — the honest curve on
    # data the strategy never saw (ADR-023). Terminal value == 1 + the scalar total return.
    strat_equity = (1.0 + fwd).cumprod()
    bh_equity = (1.0 + bh).cumprod()
    forward_equity = [
        ForwardEquityPoint(
            timestamp=ts.to_pydatetime(),
            strategy_equity=float(strat_equity.iloc[i]),
            buy_and_hold_equity=float(bh_equity.iloc[i]),
        )
        for i, ts in enumerate(fwd.index)
    ]
    n_trades = _forward_trades(result.position, forward_mask)
    return ForwardScore(
        forward_bars=int(forward_mask.sum()),
        forward_return=float((1.0 + fwd).prod() - 1.0),
        forward_sharpe=fwd_sharpe,
        buy_and_hold_return=float((1.0 + bh).prod() - 1.0),
        buy_and_hold_sharpe=bh_sharpe,
        # ADR-073: on zero trades `fwd_sharpe` is 0.0 by the degenerate-series guard, and
        # `0.0 > bh_sharpe` scored not-participating-in-a-decline as a win. Never traded, never beat.
        beats_buy_and_hold=bool(n_trades > 0 and fwd_sharpe > bh_sharpe),
        as_of=as_of,
        forward_equity=forward_equity,
        forward_trades=n_trades,
    )


class JsonFilePaperPortfolio:
    """Persisted paper-trading portfolio (ADR-019): frozen positions + their latest forward score,
    JSON-backed in-repo (reviewable in git). Single-process, mirroring the experiment store."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def positions(self) -> list[PaperPosition]:
        if not self._path.exists():
            return []
        return [PaperPosition.model_validate(item) for item in json.loads(self._path.read_text())]

    def save(self, positions: list[PaperPosition]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump(mode="json") for p in positions]
        # Trailing newline (end-of-file-fixer), same as the experiment store.
        self._path.write_text(json.dumps(payload, indent=2) + "\n")

    def add(self, position: PaperPosition) -> bool:
        """Freeze a position; no-op (returns False) if that symbol+strategy is already frozen."""
        positions = self.positions()
        if any(
            p.symbol == position.symbol and p.strategy_name == position.strategy_name
            for p in positions
        ):
            return False
        positions.append(position)
        self.save(positions)
        return True
