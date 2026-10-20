"""ADR-333: genuine no-fold absence must not hide invalid numerical evidence."""

from typing import ClassVar

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.base import BaseStrategy
from app.research.strategies.sma import SMAStrategy
from app.validation import engine, purged_cv
from app.validation.engine import ValidationEngine


class PrefixExposure(BaseStrategy):
    name: ClassVar[str] = "synthetic_prefix_exposure"
    research_citations: ClassVar[list[str]] = ["Deterministic causal refusal-path fixture"]

    def __init__(self, exposure: int) -> None:
        self.exposure = exposure

    @property
    def parameters(self) -> dict[str, object]:
        return {"exposure": self.exposure}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series(
            np.where(np.arange(len(data)) < 10, 1e-170, self.exposure), index=data.index
        )


def _frame(n: int = 300) -> pd.DataFrame:
    return pd.DataFrame(
        {"close": 100 * np.cumprod(1 + np.random.default_rng(0).normal(0.0002, 0.01, n))},
        index=pd.date_range("2024-01-01", periods=n, tz="UTC"),
    )


def test_actual_numeric_refusal_is_not_published_as_absent_geometry() -> None:
    splits = purged_cv.purged_kfold_splits(300, 5, 230)
    assert [(len(a), len(b)) for a, b in splits] == [
        (10, 60),
        (0, 60),
        (0, 60),
        (0, 60),
        (10, 60),
    ]
    with pytest.raises(ValueError, match="nonconstant returns must have measurable"):
        ValidationEngine(embargo=230).validate(
            "synthetic_prefix_exposure", [PrefixExposure(1), PrefixExposure(-1)], _frame()
        )


def test_genuine_absence_has_a_semantic_value_error_subtype() -> None:
    performance = np.zeros((8, 2))
    splits = purged_cv.purged_kfold_splits(8, 2, 100)
    with pytest.raises(ValueError, match="every fold was purged away") as refusal:
        purged_cv.purged_cv_evaluate(performance, splits, embargo=100)
    assert type(refusal.value) is getattr(purged_cv, "NoUsablePurgedFoldsError", None)


@pytest.mark.parametrize("problem", ["source", "benchmark", "embargo", "rows", "mask"])
def test_malformed_empty_fold_evidence_still_refuses_before_absence(problem: str) -> None:
    performance = np.zeros((8, 2))
    benchmark = np.zeros(8)
    splits = [(np.array([], dtype=np.intp), np.arange(8, dtype=np.intp))]
    embargo = 100
    if problem == "source":
        performance[0, 0] = np.nan
    elif problem == "benchmark":
        benchmark[0] = np.inf
    elif problem == "embargo":
        embargo = -1
    elif problem == "rows":
        splits[0] = (np.array([], dtype=np.intp), np.array([8], dtype=np.intp))
    else:
        splits[0] = (np.array([], dtype=np.intp), np.ma.array(np.arange(8), mask=[True] * 8))
    with pytest.raises(ValueError) as refusal:
        purged_cv.purged_cv_evaluate(performance, splits, embargo=embargo, benchmark=benchmark)
    assert type(refusal.value) is ValueError
    assert "every fold was purged away" not in str(refusal.value)


def test_unrelated_evaluator_refusal_propagates_through_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise ValueError("unrelated diagnostic evidence refusal")

    monkeypatch.setattr(engine, "purged_cv_evaluate", refuse)
    with pytest.raises(ValueError, match="unrelated diagnostic evidence refusal"):
        ValidationEngine().validate(
            "sma_crossover", [SMAStrategy(3, 50), SMAStrategy(5, 60)], _frame()
        )


def test_genuine_engine_absence_retains_null_count_and_geometry_flag() -> None:
    report = ValidationEngine().validate(
        "sma_crossover", [SMAStrategy(3, 50), SMAStrategy(5, 60)], _frame(60)
    )
    assert report.purged_cv is None
    assert report.n_purged_folds == 0
    assert (
        "purged CV not measured: 60 bars cannot hold 5 folds plus a 60-bar embargo" in report.flags
    )


@given(scale=st.floats(min_value=1e-175, max_value=1e-165))
def test_nonconstant_underflow_is_numeric_refusal_with_usable_folds(scale: float) -> None:
    returns = np.tile(np.array([-1.0, 0.0, 1.0, 2.0]) * scale, 2)
    performance = np.column_stack([returns, -returns])
    splits = purged_cv.purged_kfold_splits(8, 2)
    assert all(len(a) == len(b) == 4 for a, b in splits)
    with pytest.raises(ValueError, match="nonconstant returns must have measurable") as refusal:
        purged_cv.purged_cv_evaluate(performance, splits, embargo=0)
    assert type(refusal.value) is ValueError
