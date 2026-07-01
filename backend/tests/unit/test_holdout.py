"""Holdout splitter (ADR-016): the most-recent tail is sealed off before any search. Search
tools receive a SearchDataHandle (in-sample only); the holdout is reachable solely via
score_on_holdout, so a leak is a type error, not a silent methodology failure."""

import pytest
from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame
from app.research.lab.holdout import (
    HoldoutScore,
    SealedHoldout,
    SearchDataHandle,
    score_on_holdout,
    split_holdout,
)
from app.research.strategies.builder import build_strategy
from app.research.strategies.configs import SMAConfig


def _frame(n: int = 1000):
    return bars_to_frame(builders.clean_series(symbol="AAPL", n=n))


def test_holdout_is_the_calendar_latest_tail_and_split_is_contiguous() -> None:
    frame = _frame(1000)
    handle, sealed = split_holdout(frame, "AAPL", holdout_fraction=0.2, min_holdout_bars=100)
    assert isinstance(handle, SearchDataHandle)
    assert isinstance(sealed, SealedHoldout)
    # 20% of 1000 = 200 bars sealed; 800 remain for search; together they reconstruct the whole.
    assert handle.n_bars == 800
    assert sealed.n_bars == 200
    # Time-ordered and disjoint: every search bar precedes every holdout bar.
    assert handle.frame.index.max() < sealed.start
    assert sealed.end == frame.index.max()  # holdout tail ends at the dataset's last bar


def test_split_rejects_an_out_of_range_fraction() -> None:
    frame = _frame(1000)
    with pytest.raises(ValueError):
        split_holdout(frame, "AAPL", holdout_fraction=1.5)


def test_holdout_floor_is_respected_over_a_small_fraction() -> None:
    frame = _frame(1000)
    _, sealed = split_holdout(frame, "AAPL", holdout_fraction=0.05, min_holdout_bars=252)
    assert sealed.n_bars == 252  # floor wins over 5% (=50)


def test_split_rejects_data_too_short_for_search_floor() -> None:
    frame = _frame(300)
    with pytest.raises(ValueError):
        split_holdout(
            frame, "AAPL", holdout_fraction=0.2, min_holdout_bars=100, min_search_bars=252
        )


def test_search_handle_exposes_only_in_sample_span() -> None:
    frame = _frame(1000)
    handle, sealed = split_holdout(frame, "AAPL", holdout_fraction=0.2, min_holdout_bars=100)
    # The handle's frame is strictly the in-sample head — it cannot see holdout rows.
    assert len(handle.frame) == handle.n_bars == 800
    assert handle.frame.index.max() < sealed.start
    assert handle.years > 0


def test_score_on_holdout_runs_the_strategy_on_the_sealed_tail_only() -> None:
    frame = _frame(1000)
    _, sealed = split_holdout(frame, "AAPL", holdout_fraction=0.2, min_holdout_bars=100)
    strategy = build_strategy(SMAConfig(fast=5, slow=20))
    score = score_on_holdout(sealed, strategy)
    assert isinstance(score, HoldoutScore)
    assert score.n_bars == 200
    assert isinstance(score.sharpe, float)
    assert isinstance(score.total_return, float)
