"""Unused expanding SMA research diagnostic, distinct from production WF (ADR-394)."""

from dataclasses import dataclass
from math import fsum, isfinite
from typing import Literal

import pandas as pd

from app.research.lab.sma_selection import (
    SMATrainWindowContinuation,
    evaluate_sma_train_window,
)
from app.validation.walk_forward import walk_forward_splits


@dataclass(frozen=True)
class SMAExpandingWindowEvaluation:
    """Ephemeral paired windows; no switched account or calibration claim."""

    n_obs: int
    windows: tuple[SMATrainWindowContinuation, ...]
    mean_oos_sharpe: float
    mean_oos_hold_sharpe: float
    method: Literal["nested-sma-native-metrics-expanding-v1"] = (
        "nested-sma-native-metrics-expanding-v1"
    )

    @property
    def n_splits(self) -> int:
        return len(self.windows)

    @property
    def n_hypotheses(self) -> int:
        return sum(window.n_hypotheses for window in self.windows)

    @property
    def n_engine_calls(self) -> int:
        return sum(window.n_engine_calls for window in self.windows)


def _mean(scores: tuple[float, ...]) -> float:
    mean = fsum(score / len(scores) for score in scores)
    if not isfinite(mean):
        raise ValueError("window mean must be finite")
    return mean


def evaluate_sma_expanding_windows(
    frame: pd.DataFrame,
    *,
    n_splits: int,
    min_train: int | None = None,
    budget: int,
    n_per_param: int,
    refine: bool,
    refine_span: float,
    cost_rate: float,
) -> SMAExpandingWindowEvaluation:
    """Compose train-only SMA adaptation over expanding windows (ADR-393/394).

    Geometry follows López de Prado (2018), ch. 12, through the existing splitter.
    Budget is per window; repeated hypotheses remain separate evaluations.
    Native paired window means are fsum(score/K), not production WF arithmetic
    or stitched account returns. Caller source/search/holdout bounds remain
    uncertified. Later failures can follow earlier compute but return no partial
    result. This unused research helper changes no production selector or gate.
    """
    splits = walk_forward_splits(len(frame), n_splits, min_train)
    windows = tuple(
        evaluate_sma_train_window(
            frame,
            train_end=int(train[-1]) + 1,
            test_end=int(test[-1]) + 1,
            budget=budget,
            n_per_param=n_per_param,
            refine=refine,
            refine_span=refine_span,
            cost_rate=cost_rate,
        )
        for train, test in splits
    )
    return SMAExpandingWindowEvaluation(
        n_obs=len(frame),
        windows=windows,
        mean_oos_sharpe=_mean(tuple(window.oos_sharpe for window in windows)),
        mean_oos_hold_sharpe=_mean(tuple(window.oos_hold_sharpe for window in windows)),
    )
