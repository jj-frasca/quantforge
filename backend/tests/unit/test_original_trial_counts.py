"""ADR-295: original discrete counts survive public boundaries without coercion or wrap."""

import math
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional import search as panel_search
from app.research.lab import search as longitudinal_search
from app.research.lab.calibration import calibration_search_version
from app.research.lab.gate import GateConfig, GraduationGate, minbtl_years
from app.research.lab.holdout import HoldoutScore
from app.research.strategies.catalog import STRATEGY_CATALOG
from app.validation.report import ValidationReport

INVALID_TYPES = [
    True,
    False,
    np.bool_(True),
    np.bool_(False),
    1.0,
    1.5,
    np.float64(1),
    Fraction(1),
    Fraction(3, 2),
    Decimal(1),
    "1",
    None,
    [],
    [1],
    np.array(1),
    np.array([1]),
]


def report(observed: float = 1.0, name: str = "momentum") -> ValidationReport:
    return ValidationReport(
        strategy_name=name,
        observed_sharpe=observed,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        n_walk_forward_splits=0,
        n_purged_folds=0,
    )


@pytest.mark.parametrize("count", [*INVALID_TYPES, 0, -1, np.int64(-1)])
@pytest.mark.parametrize("observed", [1.0, 0.0, -1.0])
def test_minbtl_invalid_original_count_refuses_before_sharpe_shortcut(
    count: Any,
    observed: float,
) -> None:
    with pytest.raises(ValueError, match="n_trials"):
        minbtl_years(count, observed)


@pytest.mark.parametrize("count", [*INVALID_TYPES, 0, -1])
def test_gate_invalid_original_count_cannot_create_a_verdict(count: Any) -> None:
    with pytest.raises(ValueError, match="n_trials"):
        GraduationGate().evaluate(
            report(),
            0.5,
            count,
            HoldoutScore(1.0, 0.1, 252, 0.2),
            GateConfig(),
        )


@pytest.mark.parametrize("prior", [*INVALID_TYPES, -1, -3, np.int64(-1)])
@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
def test_search_invalid_original_prior_refuses_before_any_work(
    monkeypatch: pytest.MonkeyPatch,
    prior: Any,
    kind: str,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("search work started before original count validation")

    if kind == "longitudinal":
        monkeypatch.setattr(longitudinal_search, "split_holdout", forbidden)

        def invoke() -> Any:
            return longitudinal_search.run_search(None, "manual", ["momentum"], prior_trials=prior)
    else:
        monkeypatch.setattr(panel_search, "_project_score_snapshot", forbidden)

        def invoke() -> Any:
            return panel_search.run_cross_sectional_search(None, prior_trials=prior)

    with pytest.raises(ValueError, match="prior_trials"):
        invoke()


@pytest.mark.parametrize(
    "count", [1, 2, 100, np.int64(2), np.uint64(2), np.uint64(np.iinfo(np.uint64).max)]
)
def test_minbtl_valid_integral_representations_preserve_python_count_results(count: Any) -> None:
    assert minbtl_years(count, 1.0) == minbtl_years(int(count), 1.0)
    assert minbtl_years(count, 0.0) == math.inf
    assert minbtl_years(count, -1.0) == math.inf


class RepricingReached(Exception):
    pass


@pytest.mark.parametrize("kind", ["longitudinal", "panel"])
@pytest.mark.parametrize(
    "prior",
    [
        0,
        42,
        np.int64(0),
        np.uint64(0),
        np.int64(42),
        np.int64(np.iinfo(np.int64).max),
        np.uint64(np.iinfo(np.uint64).max),
    ],
)
def test_public_search_normalizes_integral_prior_before_lifetime_addition(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    prior: Any,
) -> None:
    """Intercept real orchestration at repricing, after actual count addition.

    All candidate work is manually stubbed; this is neither a search measurement
    nor a helper-only proof that could miss a discarded normalized return value.
    """
    seen = []

    def capture(finalists: Any, candidates: Any, lifetime: Any) -> Any:
        seen.append((lifetime, len(candidates)))
        raise RepricingReached

    if kind == "longitudinal":
        module = longitudinal_search
        monkeypatch.setattr(
            module, "split_holdout", lambda *args: (SimpleNamespace(frame=None), None)
        )
        monkeypatch.setattr(module.ValidationEngine, "validate", lambda *args: report())
        monkeypatch.setattr(
            module,
            "_score_configs",
            lambda configs, *args: (
                configs[0],
                [0.1] * len(configs),
                None,
                [np.zeros(8)] * len(configs),
            ),
        )

        def invoke() -> Any:
            return module.run_search(
                None, "manual", ["momentum"], n_per_param=2, prior_trials=prior
            )

        expected_current = 4
    else:
        module = panel_search
        strategy = SimpleNamespace(
            param_grid=[{"lookback": 2}, {"lookback": 3}], build=lambda params: lambda frame: None
        )
        monkeypatch.setattr(module, "default_strategies", lambda **kwargs: {"xs_manual": strategy})
        frame = pd.DataFrame({"A": [1.0, 2.0, 3.0, 4.0], "B": [4.0, 3.0, 2.0, 1.0]})
        monkeypatch.setattr(module, "split_panel_holdout", lambda prices: (frame, frame))
        monkeypatch.setattr(
            module, "_config_returns", lambda *args: pd.Series([0.1, -0.1, 0.2, -0.2])
        )
        monkeypatch.setattr(
            module, "_build_report", lambda *args, **kwargs: report(name="xs_manual")
        )
        monkeypatch.setattr(module, "rank_ic", lambda *args: None)
        monkeypatch.setattr(module, "summarize_ic", lambda *args: None)

        def invoke() -> Any:
            return module.run_cross_sectional_search(frame, quantiles=[0.2], prior_trials=prior)

        expected_current = 2
    monkeypatch.setattr(module, "whole_search_deflated_sharpes", capture)
    with pytest.raises(RepricingReached):
        invoke()
    assert seen == [(int(prior) + expected_current, expected_current)]
    assert type(seen[0][0]) is int


@given(
    st.integers(min_value=1, max_value=10**6),
    st.integers(min_value=0, max_value=10**6),
    st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False),
)
def test_minbtl_ordinary_count_increase_never_reduces_required_history(
    count: int,
    additional: int,
    sharpe: float,
) -> None:
    assert minbtl_years(count + additional, sharpe) >= minbtl_years(count, sharpe)


@given(
    st.integers(min_value=1, max_value=10**6),
    st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.5, max_value=2, allow_nan=False, allow_infinity=False),
)
def test_minbtl_ordinary_sharpe_scaling_is_inverse_square(
    count: int, sharpe: float, scale: float
) -> None:
    assert minbtl_years(count, sharpe * scale) == pytest.approx(
        minbtl_years(count, sharpe) / scale**2
    )


def test_count_boundary_change_retains_default_gate_and_v14_search_identity() -> None:
    config = GateConfig()
    assert config.version_hash == "250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493"
    assert (
        calibration_search_version(
            sorted(entry.name for entry in STRATEGY_CATALOG),
            n_per_param=3,
            config=config,
            refine=True,
            refine_span=0.25,
            select_by="observed",
        )
        == "edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459"
    )
