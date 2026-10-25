"""ADR-369: each ranked row describes the finalist whose verdict it carries."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from app.api.v1 import graduates, lab
from app.research.lab.experiment import Experiment, Graduate, PartitionedExperimentStore, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.pool_report import summarize_pool
from app.research.lab.universe import expected_max_sharpe_under_null, rank_experiments


def _experiment(
    *,
    symbol: str = "SYNTH",
    margins: tuple[float, ...] = (0.8, 0.2),
    selected: int | None = 1,
    same_family: bool = False,
    graduated: bool = False,
    holdout: float = 2.0,
) -> Experiment:
    trials = [
        Trial(
            strategy_name="sma" if same_family or i % 2 == 0 else "momentum",
            parameters={"window": 10 + i},
            observed_sharpe=margin + 1.0,
            deflated_sharpe=margin,
            pbo=0.1,
            parameter_stability_score=0.8,
        )
        for i, margin in enumerate(margins)
    ]
    finalist = trials[selected if selected is not None else margins.index(max(margins))]
    gate = (
        GateResult(
            passed=True,
            dsr_ok=True,
            pbo_ok=True,
            stability_ok=True,
            mintrl_ok=True,
            holdout_ok=True,
            required_track_record_years=1.0,
            gate_config_version=GateConfig().version_hash,
            holdout_sharpe=holdout,
            holdout_n_bars=1008,
        )
        if graduated
        else None
    )
    graduate = (
        Graduate(
            strategy_name=finalist.strategy_name,
            parameters=finalist.parameters,
            gate_result=gate,
            holdout_sharpe=holdout,
            holdout_total_return=0.2,
            holdout_n_bars=1008,
        )
        if gate is not None
        else None
    )
    return Experiment(
        symbol=symbol,
        strategy_names=[trial.strategy_name for trial in trials],
        gate_config=GateConfig(),
        trials=trials,
        lifetime_trials=len(trials),
        selected_trial_index=selected,
        best_strategy_name=finalist.strategy_name if selected is not None else None,
        best_gate_result=gate,
        graduate=graduate,
    )


@pytest.mark.parametrize("graduated", [False, True])
@pytest.mark.parametrize("same_family", [False, True])
def test_rank_experiments_selected_trial_preserves_identity_after_json_reload(
    graduated: bool, same_family: bool
) -> None:
    experiment = _experiment(graduated=graduated, same_family=same_family)
    experiment = Experiment.model_validate_json(experiment.model_dump_json())
    before = experiment.model_dump_json()
    row = rank_experiments([experiment])[0]
    selected = experiment.trials[1]
    assert row.strategy_name == selected.strategy_name
    assert row.deflated_sharpe == selected.deflated_sharpe
    assert row.graduated is graduated
    assert row.holdout_sharpe == (2.0 if graduated else None)
    assert row.survives_universe_deflation == (True if graduated else None)
    assert experiment.model_dump_json() == before


@pytest.mark.parametrize("selected", [0, None])
def test_rank_experiments_default_and_legacy_payloads_remain_exact(selected: int | None) -> None:
    experiment = _experiment(selected=selected)
    before = experiment.model_dump_json()
    assert rank_experiments([experiment])[0].model_dump(mode="json") == {
        "symbol": "SYNTH",
        "strategy_name": "sma",
        "deflated_sharpe": 0.8,
        "graduated": False,
        "holdout_sharpe": None,
        "survives_universe_deflation": None,
        "undervaluation_score": None,
    }
    assert experiment.model_dump_json() == before


@pytest.mark.parametrize("graduated", [False, True])
def test_rank_experiments_collapses_by_selected_margin(graduated: bool) -> None:
    wrong_winner = _experiment(margins=(0.9, 0.2), graduated=graduated, holdout=0.1)
    correct_winner = _experiment(margins=(0.7, 0.6), graduated=graduated)
    pad = _experiment(symbol="PAD", selected=0)
    for experiments in ([wrong_winner, correct_winner, pad], [pad, correct_winner, wrong_winner]):
        rows = rank_experiments(experiments)
        assert [row.symbol for row in rows] == (["SYNTH", "PAD"] if graduated else ["PAD", "SYNTH"])
        row = next(row for row in rows if row.symbol == "SYNTH")
        assert row.deflated_sharpe == 0.6
        assert row.strategy_name == "momentum"
        assert row.holdout_sharpe == (2.0 if graduated else None)
        assert row.survives_universe_deflation == (True if graduated else None)
        if graduated:
            assert 0.1 < expected_max_sharpe_under_null(2, 4.0) < 2.0


def test_summarize_pool_counts_the_selected_margin_representative() -> None:
    experiments = [
        _experiment(margins=(0.9, 0.2), graduated=True, holdout=0.1),
        _experiment(margins=(0.7, 0.6), graduated=True),
        _experiment(symbol="PAD", selected=0),
    ]
    report = summarize_pool(experiments, [])
    assert report.n_graduate_experiments == 2
    assert report.n_leaderboard_graduates == 1
    assert report.n_surviving_deflation == 1


@pytest.mark.parametrize("endpoint", ["leaderboard", "graduates"])
def test_public_ranked_endpoint_preserves_stored_selected_graduate(
    tmp_path: Path, endpoint: str
) -> None:
    pool = tmp_path / "pool"
    experiment = _experiment(graduated=True)
    PartitionedExperimentStore(pool).add(experiment)
    application = FastAPI()
    application.include_router(lab.router, prefix="/api/v1")
    application.include_router(graduates.router, prefix="/api/v1")
    application.dependency_overrides[lab.get_pool_path] = lambda: pool
    application.dependency_overrides[graduates.get_pool_path] = lambda: pool
    response = TestClient(application).get(f"/api/v1/{endpoint}")
    assert response.status_code == 200
    row = response.json()[0]
    assert row["strategy_name"] == "momentum"
    assert row["deflated_sharpe"] == 0.2
    assert row["holdout_sharpe"] == 2.0
    assert row["survives_universe_deflation"] is True
    assert (
        PartitionedExperimentStore(pool).all()[0].model_dump_json() == experiment.model_dump_json()
    )


@given(
    margins=st.lists(st.floats(min_value=-5, max_value=5, allow_nan=False), min_size=2, max_size=8),
    index=st.integers(min_value=0, max_value=7),
    same_family=st.booleans(),
)
def test_rank_experiments_arbitrary_trial_order_preserves_selected_identity(
    margins: list[float], index: int, same_family: bool
) -> None:
    selected = index % len(margins)
    experiment = _experiment(margins=tuple(margins), selected=selected, same_family=same_family)
    before = experiment.model_dump_json()
    row = rank_experiments([experiment])[0]
    assert row.deflated_sharpe == margins[selected]
    assert row.strategy_name == experiment.trials[selected].strategy_name
    assert experiment.model_dump_json() == before


def test_rank_experiments_empty_trials_still_skip() -> None:
    empty = Experiment(
        symbol="EMPTY", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    assert rank_experiments([empty]) == []
