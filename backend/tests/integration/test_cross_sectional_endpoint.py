"""Read-only cross-sectional endpoint (ADR-024): surface the LATEST cross-sectional hunt — its
per-strategy trials, graduation verdict, and universe size — for the dashboard. Reads the committed
JSON pool with a dependency-injected path; an empty/missing pool returns null, never a 500."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.cross_sectional import get_pool_path
from app.main import app
from app.research.cross_sectional.ic import ICSummary
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.lab.gate import GateConfig


def _trial(name: str, deflated: float, ic: ICSummary | None = None) -> CrossSectionalTrial:
    return CrossSectionalTrial(
        strategy_name=name,
        parameters={"lookback": 60, "quantile": 0.2},
        observed_sharpe=0.5,
        deflated_sharpe=deflated,
        pbo=0.3,
        parameter_stability_score=0.6,
        ic=ic,
    )


def _experiment(created: datetime, universe: list[str], best: str) -> CrossSectionalExperiment:
    return CrossSectionalExperiment(
        created_at=created,
        universe_symbols=universe,
        strategy_names=["xs_momentum", "xs_reversal"],
        gate_config=GateConfig(),
        trials=[_trial("xs_momentum", 0.1), _trial("xs_reversal", -1.6)],
        lifetime_trials=42,
        best_strategy_name=best,
        graduate=None,
    )


def test_default_pool_path_points_at_the_in_repo_data_dir() -> None:
    assert get_pool_path().name == "cross_sectional_pool.json"
    assert get_pool_path().parent.name == "data"


def test_returns_latest_experiment_trials_and_universe_size(tmp_path) -> None:
    pool = tmp_path / "cs.json"
    store = JsonFileCrossSectionalStore(pool)
    store.add(_experiment(datetime(2026, 1, 1, tzinfo=UTC), ["AAPL", "MSFT"], "xs_reversal"))
    store.add(
        _experiment(datetime(2026, 7, 1, tzinfo=UTC), ["AAPL", "MSFT", "NVDA"], "xs_momentum")
    )
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        body = TestClient(app).get("/api/v1/cross-sectional").json()
        # Latest by created_at wins (3-name universe, best = xs_momentum).
        assert body["universe_size"] == 3
        assert body["best_strategy_name"] == "xs_momentum"
        assert body["graduated"] is False
        assert body["graduate_holdout_sharpe"] is None
        assert [t["strategy_name"] for t in body["trials"]] == ["xs_momentum", "xs_reversal"]
        assert body["trials"][0]["deflated_sharpe"] == 0.1
        assert body["trials"][0]["pbo"] == 0.3
    finally:
        app.dependency_overrides.clear()


def test_returns_null_when_pool_file_absent(tmp_path) -> None:
    app.dependency_overrides[get_pool_path] = lambda: tmp_path / "nope.json"
    try:
        response = TestClient(app).get("/api/v1/cross-sectional")
        assert response.status_code == 200
        assert response.json() is None
    finally:
        app.dependency_overrides.clear()


def test_returns_null_when_pool_is_empty(tmp_path) -> None:
    pool = tmp_path / "cs.json"
    pool.write_text("[]\n")
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        assert TestClient(app).get("/api/v1/cross-sectional").json() is None
    finally:
        app.dependency_overrides.clear()


def test_rank_ic_is_surfaced_per_trial_and_is_null_when_not_measured(tmp_path) -> None:
    # ADR-035: the IC answers "did the ranking carry information", which the Sharpe columns cannot.
    # A trial written before that ADR has no IC and must read as absent, never as zero.
    ic = ICSummary(
        mean=0.021, std=0.14, information_ratio=0.15, t_stat=3.4, hit_rate=0.54, n_periods=500
    )
    experiment = _experiment(datetime(2026, 7, 1, tzinfo=UTC), ["AAPL", "MSFT"], "xs_momentum")
    scored = experiment.model_copy(
        update={"trials": [_trial("xs_momentum", 0.1, ic), _trial("xs_reversal", -1.6)]}
    )
    pool = tmp_path / "cs.json"
    JsonFileCrossSectionalStore(pool).add(scored)
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        trials = TestClient(app).get("/api/v1/cross-sectional").json()["trials"]
        assert trials[0]["ic_mean"] == 0.021
        assert trials[0]["ic_t_stat"] == 3.4
        assert trials[1]["ic_mean"] is None
        assert trials[1]["ic_t_stat"] is None
    finally:
        app.dependency_overrides.clear()
