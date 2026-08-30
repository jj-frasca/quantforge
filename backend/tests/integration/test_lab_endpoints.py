"""Read-only lab endpoints (WP-D): expose the research-pool leaderboard + the paper portfolio for
the dashboard. They read the committed JSON stores; paths are dependency-injected for tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.lab import (
    get_calibration_path,
    get_pool_path,
    get_portfolio_path,
    get_power_calibration_path,
)
from app.main import app
from app.research.lab.calibration import (
    NullCalibration,
    PowerCalibration,
    collect_power_sweep,
)
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


def _calibration_json(mode: str, n_graduates: int, n_bars: int | None = None) -> str:
    return NullCalibration(
        n_symbols=200,
        n_graduates=n_graduates,
        false_graduation_rate=n_graduates / 200,
        n_clear_deflation_bar=0,
        deflation_bar=2.11,
        max_deflated_sharpe=0.92,
        max_holdout_sharpe=0.85,
        graduates=[],
        holdout_years=[2.4],
        n_bars=[] if n_bars is None else [n_bars],
        walk_forward_oos_sharpes=[0.1, 0.2, 0.3],
        purged_cv_oos_sharpes=[0.2, 0.3, 0.4],
        errors={},
        gate_config_version="v1",
        null_mode=mode,
    ).model_dump_json()


def test_null_calibration_endpoint_returns_every_measured_mode(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "iid_normal.json").write_text(_calibration_json("iid_normal", 2))
    (tmp_path / "bootstrap.json").write_text(_calibration_json("bootstrap:SPY", 2))
    app.dependency_overrides[get_calibration_path] = lambda: tmp_path

    response = TestClient(app).get("/api/v1/null-calibration")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert {row["null_mode"] for row in body} == {"iid_normal", "bootstrap:SPY"}
    assert all(row["false_graduation_rate"] == 0.01 for row in body)
    assert all(row["n_clear_deflation_bar"] == 0 for row in body)
    assert all(row["search_config_version"] == "legacy-unspecified" for row in body)


def test_null_calibration_endpoint_retains_histories_for_the_same_mode(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "iid_normal_5400.json").write_text(_calibration_json("iid_normal", 2, 5400))
    (tmp_path / "iid_normal_7400.json").write_text(_calibration_json("iid_normal", 0, 7400))
    app.dependency_overrides[get_calibration_path] = lambda: tmp_path

    response = TestClient(app).get("/api/v1/null-calibration")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [row["n_bars"] for row in response.json()] == [[5400], [7400]]


def test_null_calibration_endpoint_is_empty_when_nothing_has_been_measured(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """An empty list is honest; a 500 would take the whole dashboard down with it."""
    app.dependency_overrides[get_calibration_path] = lambda: tmp_path / "missing"
    response = TestClient(app).get("/api/v1/null-calibration")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


# --- ADR-053: the measured power curve, served beside the measured Type-I error ---


def _sweep_json(edge: str, keys: list[float]) -> str:
    cells = [
        PowerCalibration(
            n_symbols=50,
            n_detected=int(50 * rate),
            detection_rate=rate,
            n_clear_deflation_bar=0,
            deflation_bar=2.11,
            edge=edge,
            phi=key if edge == "ar1" else None,
            half_life=None if edge == "ar1" else key,
            oracle_sharpes=[2.0] * 50,
            holdout_years=[4.3] * 50,
            n_bars=[5400] * 50,
            errors={},
            gate_config_version="v1",
            search_config_version="search-v1",
        )
        for key, rate in zip(keys, (0.1, 0.2), strict=True)
    ]
    return collect_power_sweep(cells).model_dump_json()


def test_power_calibration_endpoint_returns_every_measured_sweep(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "ar1.json").write_text(_sweep_json("ar1", [-0.3, 0.3]))
    (tmp_path / "band_reversion.json").write_text(_sweep_json("band_reversion", [1.0, 5.0]))
    app.dependency_overrides[get_power_calibration_path] = lambda: tmp_path

    response = TestClient(app).get("/api/v1/power-calibration")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert {sweep["edge"] for sweep in body} == {"ar1", "band_reversion"}
    assert all(sweep["n_bars"] == 5400 for sweep in body)
    assert [cell["detection_rate"] for cell in body[0]["cells"]] == [0.1, 0.2]


def test_power_calibration_endpoint_is_empty_when_nothing_has_been_measured(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Same contract as the null endpoint: an absent measurement is [] and 200, never a 500 that
    takes the dashboard down."""
    app.dependency_overrides[get_power_calibration_path] = lambda: tmp_path / "missing"
    response = TestClient(app).get("/api/v1/power-calibration")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
