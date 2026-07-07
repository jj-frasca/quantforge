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
from app.research.strategies.builder import build_strategy_from_dict


class ForwardScore(BaseModel):
    """A frozen strategy's out-of-time performance (ADR-019), scored ONLY on bars after the freeze
    date — data it could not have been fit to. `beats_buy_and_hold` is the honest bar: did the
    strategy earn more than simply holding the name, risk-adjusted, going forward?"""

    model_config = ConfigDict(frozen=True)

    forward_bars: int
    forward_return: float
    forward_sharpe: float
    buy_and_hold_return: float
    buy_and_hold_sharpe: float
    beats_buy_and_hold: bool
    as_of: datetime


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


class ExitPolicy(BaseModel):
    """Tunable, versioned exit rules (ADR-020) — the risk discipline that cuts a decaying strategy.
    Same calibration philosophy as GateConfig (ADR-015)."""

    model_config = ConfigDict(frozen=True)

    min_forward_bars_before_exit: int = 21  # ~1mo grace: don't cut on entry noise
    rolling_window_bars: int = 63  # ~3mo trailing window for "recent" performance
    min_rolling_sharpe: float = 0.0
    max_forward_drawdown: float = 0.25
    require_beat_buy_and_hold_forward: bool = True

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
    forward_returns: pd.Series, buy_and_hold_returns: pd.Series, policy: ExitPolicy
) -> LifecycleDecision:
    """Decide hold/exit from a position's FORWARD returns (ADR-020). Uses a rolling trailing window
    so recent decay isn't masked by early gains. Pure — no engine/network, fully controllable."""
    n = len(forward_returns)
    if n < policy.min_forward_bars_before_exit:
        return LifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_buy_and_hold_sharpe=0.0,
            reasons=["grace period (insufficient forward data)"],
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
    return lifecycle_from_returns(fwd, bh, policy)


def freeze_graduate(experiment: Experiment, frozen_at: datetime) -> PaperPosition:
    """Turn a graduated Experiment into a paper position frozen as of `frozen_at`."""
    if experiment.graduate is None:
        raise ValueError(f"experiment for {experiment.symbol!r} has no graduate to freeze")
    g = experiment.graduate
    return PaperPosition(
        symbol=experiment.symbol,
        strategy_name=g.strategy_name,
        parameters=g.parameters,
        frozen_at=frozen_at,
    )


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
        )

    strategy = build_strategy_from_dict(position.strategy_name, position.parameters)
    result = BacktestEngine().run_strategy(frame, strategy)

    fwd = result.returns[forward_mask]
    bh = frame["close"].pct_change().fillna(0.0)[forward_mask]
    fwd_sharpe = sharpe_ratio(fwd)
    bh_sharpe = sharpe_ratio(bh)
    return ForwardScore(
        forward_bars=int(forward_mask.sum()),
        forward_return=float((1.0 + fwd).prod() - 1.0),
        forward_sharpe=fwd_sharpe,
        buy_and_hold_return=float((1.0 + bh).prod() - 1.0),
        buy_and_hold_sharpe=bh_sharpe,
        beats_buy_and_hold=fwd_sharpe > bh_sharpe,
        as_of=as_of,
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
