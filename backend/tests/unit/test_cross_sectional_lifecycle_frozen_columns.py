"""Direct lifecycle decisions retain the frozen ranked universe (ADR-363)."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy,
    CrossSectionalPosition,
    evaluate_cross_sectional_lifecycle,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "A": 100.0 * np.cumprod([1, 1.01, 1.03, 1.01, 1.03, 1.01, 1.03, 1.01]),
            "B": 100.0,
            "C": 100.0 * np.cumprod([1, 0.99, 0.97, 0.99, 0.97, 0.99, 0.97, 0.99]),
            "D": 100.0,
        },
        index=pd.date_range("2026-01-01", periods=8, tz="UTC"),
    )


def _position(panel: pd.DataFrame, freeze: int = 2) -> CrossSectionalPosition:
    return CrossSectionalPosition(
        strategy_name="xs_value",
        parameters={"quantile": 0.25},
        universe_symbols=tuple(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[freeze].to_pydatetime(),
        value_scores={"A": 1.0, "B": 0.8, "C": 0.2, "D": 0.0},
    )


def _policy() -> CrossSectionalExitPolicy:
    return CrossSectionalExitPolicy(
        min_forward_bars_before_exit=0,
        rolling_window_bars=3,
        require_beat_benchmark_forward=False,
    )


@pytest.mark.parametrize("freeze", [2, 7])
@pytest.mark.parametrize(
    "columns",
    [
        ["C", "D"],
        ["A", "B", "C", "D", "E"],
        ["E", "B", "C", "D"],
        ["D", "C", "B", "A"],
        ["A", "B", "C", "C"],
        ["a", "B", "C", "D"],
        [" A", "B", "C", "D"],
        [],
    ],
    ids=["subset", "extra", "substituted", "reordered", "duplicate", "case", "space", "empty"],
)
def test_lifecycle_given_changed_frozen_columns_refuses_before_any_verdict(
    freeze: int, columns: Sequence[str]
) -> None:
    panel = _panel()
    position = _position(panel, freeze)
    changed = pd.DataFrame(100.0, index=panel.index, columns=columns)
    with pytest.raises(ValueError, match="exact frozen universe order"):
        evaluate_cross_sectional_lifecycle(position, changed, _policy())


def test_lifecycle_given_wrong_universe_refuses_before_calendar_access() -> None:
    panel = _panel()
    position = _position(panel)
    changed = panel[["C", "D"]].set_axis(["not a timestamp"] * len(panel))
    with pytest.raises(ValueError, match="exact frozen universe order"):
        evaluate_cross_sectional_lifecycle(position, changed, _policy())


def test_lifecycle_given_invalid_policy_keeps_policy_validation_first() -> None:
    panel = _panel()
    invalid = _policy().model_copy(update={"rolling_window_bars": 0})
    with pytest.raises(ValueError, match="rolling_window_bars"):
        evaluate_cross_sectional_lifecycle(_position(panel), panel[["C", "D"]], invalid)


def test_lifecycle_given_subset_cannot_retire_a_different_frozen_factor() -> None:
    panel = _panel()
    position = _position(panel)
    complete = evaluate_cross_sectional_lifecycle(position, panel, _policy())
    assert complete.action == "hold"
    assert complete.rolling_sharpe == pytest.approx(22.912878474779202)
    assert complete.forward_drawdown == 0.0
    with pytest.raises(ValueError, match="exact frozen universe order"):
        evaluate_cross_sectional_lifecycle(position, panel[["C", "D"]], _policy())


@pytest.mark.parametrize("freeze", [2, 6, 7])
def test_lifecycle_given_matching_panel_preserves_grace_and_measured_decisions(freeze: int) -> None:
    panel = _panel()
    position = _position(panel, freeze)
    before = panel.copy(deep=True)
    position_before = position.model_dump_json()
    decision = evaluate_cross_sectional_lifecycle(position, panel, CrossSectionalExitPolicy())
    assert decision.action == "hold"
    assert decision.rolling_sharpe == 0.0
    assert decision.forward_drawdown == 0.0
    assert decision.reasons == [
        "grace period (no forward data)"
        if freeze == 7
        else "grace period (insufficient forward data)"
    ]
    pd.testing.assert_frame_equal(panel, before, check_exact=True)
    assert position.model_dump_json() == position_before


@given(st.permutations(("A", "B", "C", "D")))
@settings(max_examples=24, deadline=None)
def test_lifecycle_given_permuted_panel_preserves_frozen_order_contract(
    columns: Sequence[str],
) -> None:
    panel = _panel()
    position = _position(panel)
    if tuple(columns) == position.universe_symbols:
        assert evaluate_cross_sectional_lifecycle(position, panel, _policy()).action == "hold"
    else:
        with pytest.raises(ValueError, match="exact frozen universe order"):
            evaluate_cross_sectional_lifecycle(position, panel[list(columns)], _policy())
