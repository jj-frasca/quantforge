import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import sharpe_ratio
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
