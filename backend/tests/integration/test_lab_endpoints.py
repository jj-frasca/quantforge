"""Read-only lab endpoints (WP-D): expose the research-pool leaderboard + the paper portfolio for
the dashboard. They read the committed JSON stores; paths are dependency-injected for tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.lab import get_pool_path, get_portfolio_path
from app.main import app
from app.research.lab.experiment import Experiment, Graduate, PartitionedExperimentStore, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import JsonFilePaperPortfolio, PaperPosition


def _graduated_experiment() -> Experiment:
    gr = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version="v",
    )
    return Experiment(
        symbol="CRM",
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={"fast": 10, "slow": 30},
                observed_sharpe=1.0,
                deflated_sharpe=0.5,
                pbo=0.1,
                parameter_stability_score=0.8,
            )
        ],
        lifetime_trials=1,
        graduate=Graduate(
            strategy_name="sma",
            parameters={"fast": 10, "slow": 30},
            gate_result=gr,
            holdout_sharpe=0.5,
            holdout_total_return=0.1,
            holdout_n_bars=252,
        ),
    )


def test_default_paths_point_at_the_in_repo_data_dir() -> None:
    assert get_pool_path().name == "research_pool"  # per-symbol partitions (ADR-032)
    assert get_portfolio_path().name == "paper_portfolio.json"
    assert get_pool_path().parent.name == "data"


def test_leaderboard_returns_ranked_rows(tmp_path) -> None:
    pool = tmp_path / "research_pool"
    PartitionedExperimentStore(pool).add(_graduated_experiment())
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        body = TestClient(app).get("/api/v1/leaderboard").json()
        assert len(body) == 1
        assert body[0]["symbol"] == "CRM"
        assert body[0]["graduated"] is True
    finally:
        app.dependency_overrides.clear()


def test_paper_portfolio_returns_positions(tmp_path) -> None:
    portfolio = tmp_path / "portfolio.json"
    JsonFilePaperPortfolio(portfolio).add(
        PaperPosition(
            symbol="LOW",
            strategy_name="rsi_mean_reversion",
            parameters={"window": 64},
            frozen_at=datetime(2026, 7, 6, tzinfo=UTC),
        )
    )
    app.dependency_overrides[get_portfolio_path] = lambda: portfolio
    try:
        body = TestClient(app).get("/api/v1/paper-portfolio").json()
        assert len(body) == 1
        assert body[0]["symbol"] == "LOW" and body[0]["status"] == "open"
    finally:
        app.dependency_overrides.clear()


def test_endpoints_are_empty_when_files_absent(tmp_path) -> None:
    app.dependency_overrides[get_pool_path] = lambda: tmp_path / "nope.json"
    app.dependency_overrides[get_portfolio_path] = lambda: tmp_path / "nope2.json"
    try:
        client = TestClient(app)
        assert client.get("/api/v1/leaderboard").json() == []
        assert client.get("/api/v1/paper-portfolio").json() == []
    finally:
        app.dependency_overrides.clear()


# ---- GET /pool-report (ADR-033: the honest headline) ---------------------------------------------


def test_pool_report_returns_the_deflation_headline(tmp_path) -> None:
    pool = tmp_path / "research_pool"
    store = PartitionedExperimentStore(pool)
    store.add(_graduated_experiment())
    app.dependency_overrides[get_pool_path] = lambda: pool
    app.dependency_overrides[get_portfolio_path] = lambda: tmp_path / "absent.json"
    try:
        response = TestClient(app).get("/api/v1/pool-report")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["n_experiments"] == 1
    assert body["n_symbols"] == 1
    assert body["n_leaderboard_graduates"] == 1
    # A single-symbol pool has no cross-symbol selection to deflate — the bar is 0, so nothing is
    # reported as a near-miss and the survivor count is not inflated by a vacuous pass.
    assert body["near_misses"] == []
    assert body["book"]["n_survivors"] == 0


def test_pool_report_is_empty_when_the_pool_is_absent(tmp_path) -> None:
    app.dependency_overrides[get_pool_path] = lambda: tmp_path / "nope"
    app.dependency_overrides[get_portfolio_path] = lambda: tmp_path / "nope2.json"
    try:
        response = TestClient(app).get("/api/v1/pool-report")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["n_experiments"] == 0
