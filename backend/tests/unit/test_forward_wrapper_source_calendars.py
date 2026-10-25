"""Original calendar identity precedes forward shortcuts (ADR-364)."""

from datetime import UTC, datetime
from typing import Literal, cast

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy,
    CrossSectionalPosition,
    evaluate_cross_sectional_lifecycle,
    score_forward,
)
from app.research.dataset import ResearchDatasetEvidence
from app.research.lab.paper import ExitPolicy, PaperPosition, evaluate_lifecycle

Wrapper = Literal["score", "panel", "single"]
_FREEZE = datetime(2026, 1, 5, tzinfo=UTC)


def _panel(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame(100.0, index=index, columns=["A", "B"])


def _position(frozen_at: datetime = _FREEZE) -> CrossSectionalPosition:
    return CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 1, "skip": 0, "quantile": 0.5},
        universe_symbols=("A", "B"),
        cost_rate=0.001,
        frozen_at=frozen_at,
    )


def _single_position(frozen_at: datetime = _FREEZE) -> PaperPosition:
    return PaperPosition(
        symbol="A",
        strategy_name="momentum",
        parameters={"lookback": 1, "skip": 0},
        frozen_at=frozen_at,
    )


def _run(wrapper: Wrapper, index: pd.Index, frozen_at: datetime = _FREEZE) -> BaseModel:
    panel = _panel(index)
    if wrapper == "score":
        return score_forward(_position(frozen_at), panel)
    if wrapper == "panel":
        return evaluate_cross_sectional_lifecycle(
            _position(frozen_at), panel, CrossSectionalExitPolicy()
        )
    return evaluate_lifecycle(
        _single_position(frozen_at), panel[["A"]].rename(columns={"A": "close"}), ExitPolicy()
    )


@pytest.mark.parametrize("wrapper", ["score", "panel", "single"])
@pytest.mark.parametrize("kind", ["duplicate", "descending", "nat"])
def test_forward_wrapper_given_invalid_pre_freeze_calendar_refuses_before_shortcut(
    wrapper: Wrapper, kind: str
) -> None:
    dates = {
        "duplicate": ["2026-01-02", "2026-01-02"],
        "descending": ["2026-01-03", "2026-01-02"],
        "nat": ["2026-01-02", None],
    }
    index = pd.DatetimeIndex(dates[kind], tz="UTC")
    with pytest.raises(ValueError, match="unique and ascending"):
        _run(wrapper, index)


@pytest.mark.parametrize("wrapper", ["score", "panel", "single"])
@pytest.mark.parametrize("dates", [["2026-01-07", "2026-01-06"], ["2026-01-06"] * 2])
def test_forward_wrapper_given_invalid_measured_calendar_keeps_refusal(
    wrapper: Wrapper, dates: list[str]
) -> None:
    with pytest.raises(ValueError, match="unique and ascending"):
        _run(wrapper, pd.DatetimeIndex(dates, tz="UTC"))


@pytest.mark.parametrize("wrapper", ["panel", "single"])
def test_forward_wrapper_given_bad_policy_preserves_policy_error_precedence(
    wrapper: Wrapper,
) -> None:
    index = pd.DatetimeIndex(["2026-01-02"] * 2, tz="UTC")
    panel = _panel(index)
    with pytest.raises(ValueError, match="rolling_window_bars"):
        if wrapper == "panel":
            evaluate_cross_sectional_lifecycle(
                _position(),
                panel,
                CrossSectionalExitPolicy().model_copy(update={"rolling_window_bars": 0}),
            )
        else:
            evaluate_lifecycle(
                _single_position(),
                panel.rename(columns={"A": "close"}),
                ExitPolicy().model_copy(update={"rolling_window_bars": 0}),
            )


@pytest.mark.parametrize("wrapper", ["score", "panel"])
def test_panel_forward_wrapper_given_bad_columns_preserves_identity_error_precedence(
    wrapper: Wrapper,
) -> None:
    panel = _panel(pd.DatetimeIndex(["2026-01-02"] * 2, tz="UTC"))[["A"]]
    with pytest.raises(ValueError, match="exact frozen universe order"):
        if wrapper == "score":
            score_forward(_position(), panel)
        else:
            evaluate_cross_sectional_lifecycle(_position(), panel, CrossSectionalExitPolicy())


def test_score_forward_given_bad_evidence_preserves_validation_before_calendar() -> None:
    panel = _panel(pd.DatetimeIndex(["2026-01-02"] * 2, tz="UTC"))
    with pytest.raises(ValueError, match="ResearchDatasetEvidence"):
        score_forward(_position(), panel, evidence=[cast(ResearchDatasetEvidence, object())])


@pytest.mark.parametrize("wrapper", ["score", "panel", "single"])
@pytest.mark.parametrize("singleton", [False, True])
def test_forward_wrapper_given_ordered_object_timestamps_preserves_no_forward_output(
    wrapper: Wrapper, singleton: bool
) -> None:
    index = pd.Index(
        [pd.Timestamp("2026-01-02", tz="US/Pacific"), pd.Timestamp("2026-01-03", tz="US/Pacific")][
            : 1 if singleton else 2
        ],
        dtype=object,
    )
    output = _run(wrapper, index).model_dump(mode="json")
    if wrapper == "score":
        assert output["forward_bars"] == 0
        assert output["as_of"] == ("2026-01-02T08:00:00Z" if singleton else "2026-01-03T08:00:00Z")
    else:
        assert output["action"] == "hold"
        assert output["rolling_sharpe"] == 0.0


@pytest.mark.parametrize("wrapper", ["panel", "single"])
@pytest.mark.parametrize("generic", [False, True])
def test_lifecycle_wrapper_given_empty_ordered_calendar_preserves_hold(
    wrapper: Wrapper, generic: bool
) -> None:
    index = pd.Index([], dtype=object) if generic else pd.DatetimeIndex([], tz="UTC")
    assert _run(wrapper, index).model_dump()["action"] == "hold"


@pytest.mark.parametrize("wrapper", ["panel", "single"])
def test_lifecycle_wrapper_given_naive_ordered_calendar_preserves_hold(wrapper: Wrapper) -> None:
    assert (
        _run(
            wrapper, pd.date_range("2026-01-02", periods=2), _FREEZE.replace(tzinfo=None)
        ).model_dump()["action"]
        == "hold"
    )


@pytest.mark.parametrize("index", [pd.DatetimeIndex([], tz="UTC"), pd.Index([], dtype=object)])
def test_score_forward_given_empty_ordered_calendar_keeps_existing_as_of_refusal(
    index: pd.Index,
) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _run("score", index)


def test_score_forward_given_naive_ordered_calendar_keeps_existing_as_of_refusal() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _run("score", pd.date_range("2026-01-02", periods=2), _FREEZE.replace(tzinfo=None))


@pytest.mark.parametrize("wrapper", ["score", "panel", "single"])
def test_forward_wrapper_given_integer_calendar_keeps_existing_cutoff_refusal(
    wrapper: Wrapper,
) -> None:
    with pytest.raises(TypeError):
        _run(wrapper, pd.Index([0, 1]))


@pytest.mark.parametrize("wrapper", ["score", "panel", "single"])
@given(st.lists(st.integers(min_value=1, max_value=3), min_size=2, max_size=5))
@settings(max_examples=25, deadline=None)
def test_forward_wrapper_calendar_identity_precedes_shortcut_for_any_date_order(
    wrapper: Wrapper, days: list[int]
) -> None:
    index = pd.DatetimeIndex([pd.Timestamp(2026, 1, day, tz="UTC") for day in days])
    if days == sorted(set(days)):
        _run(wrapper, index)
    else:
        with pytest.raises(ValueError, match="unique and ascending"):
            _run(wrapper, index)
